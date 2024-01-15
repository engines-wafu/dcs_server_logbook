import hashlib, random, sqlite3
import numpy as np
from PIL import Image, ImageOps
from matplotlib.colors import to_rgb

class ribbonGenerator:
    def __init__(self, input_string, image_size=(64, 190), color_array=None, min_block_width_percent=3, max_block_width_percent=20):
        self.input_string = input_string
        self.image_size = image_size
        self.hash_string = self._string_to_hash(input_string)
        self.num_blocks = self._determine_number_of_blocks()
        self.color_array = color_array if color_array else ['#FF0000', '#00FF00', '#0000FF']
        self.min_block_width = (min_block_width_percent / 100) * self.image_size[1]
        self.max_block_width = (max_block_width_percent / 100) * self.image_size[1]

    @staticmethod
    def _string_to_hash(input_string):
        """Converts a string to a hash using SHA-256 algorithm."""
        return hashlib.sha256(input_string.encode()).hexdigest()

    def _determine_number_of_blocks(self):
        """Uses the hash to seed a random number generator and determines the number of color blocks."""
        hash_int = int(self.hash_string, 16)
        random.seed(hash_int)
        return random.randint(2, 14)

    def _hash_to_color_and_width_blocks(self):
        colors = random.choices(self.color_array, k=self.num_blocks)

        # Calculate the total width for blocks
        remaining_width = self.image_size[1]
        widths = []

        for _ in range(self.num_blocks):
            # If the remaining width is less than the minimum block width, use the remaining width
            if remaining_width < self.min_block_width:
                widths.append(remaining_width)
                break

            # Ensure the last block takes the remaining width
            if len(widths) == self.num_blocks - 1:
                widths.append(remaining_width)
                break

            # Calculate width for this block
            max_width_for_block = min(int(self.max_block_width), remaining_width)
            width = random.randint(int(self.min_block_width), max_width_for_block)
            widths.append(width)
            remaining_width -= width

        return list(zip(colors, widths))

    def create_variable_width_symmetrical_pattern(self):
        """Creates a pattern with variable number and width of color blocks."""
        colors_and_widths = self._hash_to_color_and_width_blocks()
        img = np.zeros((self.image_size[0], self.image_size[1], 3), dtype=np.uint8)

        current_x = 0
        for color, width in colors_and_widths:
            end_x = min(current_x + width, self.image_size[1])
            img[:, current_x:end_x] = np.array(to_rgb(color)) * 255
            current_x = end_x

        # Ensure the pattern is symmetrical
        img = np.concatenate((np.flip(img, axis=1), img), axis=1)
        return img

    def fetch_award_names(self, db_path):
        """Fetches all award names from the Awards table in the database."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT award_name FROM Awards")
            rows = cursor.fetchall()
            conn.close()
            return [row[0] for row in rows]
        except Exception as e:
            print(f"Error: {e}")
            return []

    def save_pattern_as_png(self, file_path):
        """Saves the generated pattern as a PNG file."""
        pattern_image = self.create_variable_width_symmetrical_pattern()
        Image.fromarray(pattern_image.astype('uint8'), 'RGB').save(file_path)

predefined_colors = [
  "#C0C0C0",  # Silver
  "#B9CCED",  # Light Steel Blue
  "#800000",  # Maroon
  "#008000",  # Green
  "#000B40",  # Navy (Updated)*
  "#DD1C1A",  # Brown (Updated)*
  "#FFB20F",  # Orange (Updated)*
  "#5A5F6F",  # Steel Blue (Updated)*
  "#514B23"   # Olive Drab (Updated)*
]

db_path = 'data/db/mayfly.db'

# Initialize the pattern generator
pattern_generator = ribbonGenerator(
    "example string",
    color_array=predefined_colors,
    min_block_width_percent=5,
    max_block_width_percent=40
)

def create_award_quilt(db_path, pilot_id):
    # Database connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch award_names for the given pilot_id
    cursor.execute("SELECT a.award_name FROM Pilot_Awards pa INNER JOIN Awards a ON pa.award_id = a.award_id WHERE pa.pilot_id = ?", (pilot_id,))
    award_names = cursor.fetchall()

    ribbons = []
    for award_name in award_names:
        try:
            ribbon_path = f'web/img/ribbons/{award_name[0]}.png'
            ribbon = Image.open(ribbon_path)

            # Add a black border around the ribbon
            border_size = 4  # Adjust the border size as needed
            ribbon = ImageOps.expand(ribbon, border=border_size, fill='black')

            ribbons.append(ribbon)
        except FileNotFoundError:
            print(f"Ribbon image not found for award_name: {award_name[0]}")

    # Check if ribbons list is empty
    if not ribbons:
        print(f"No ribbon images found for pilot_id: {pilot_id}")
        return

    # Calculate quilt dimensions and spacing
    num_ribbons = len(ribbons)
    ribbon_width, ribbon_height = ribbons[0].size
    spacing = 5  # Spacing between ribbons

    row_width = min(3, num_ribbons)  # Max 3 ribbons per row
    num_rows = (num_ribbons + 2) // 3
    quilt_width = row_width * ribbon_width + (row_width - 1) * spacing
    quilt_height = num_rows * ribbon_height + (num_rows - 1) * spacing

    # Create a new image for the quilt with transparent background
    quilt = Image.new('RGBA', (quilt_width, quilt_height), (0, 0, 0, 0))

    # Calculate the number of ribbons in the top row
    top_row_ribbons = num_ribbons % 3 or 3
    start_index = 0

    # Arrange ribbons in the quilt
    for i in range(num_rows):
        ribbons_in_row = top_row_ribbons if i == 0 else 3
        # Center the ribbons in the current row
        offset = (quilt_width - (ribbons_in_row * ribbon_width + (ribbons_in_row - 1) * spacing)) // 2
        for j in range(ribbons_in_row):
            x = offset + j * (ribbon_width + spacing)
            y = i * (ribbon_height + spacing)
            quilt.paste(ribbons[start_index + j], (x, y))
        start_index += ribbons_in_row


    # Resize the quilt
    scale_factor = 0.25
    new_size = (int(quilt.width * scale_factor), int(quilt.height * scale_factor))
    quilt = quilt.resize(new_size, Image.Resampling.LANCZOS)

    # Save the quilt
    filename = f'web/img/fruit_salad/{pilot_id}.png'
    quilt.save(filename)

    # Close the database connection
    conn.close()

# Example usage
# create_award_quilt('example_pilot_id')

# Fetch award names using the instance of the pattern generator
award_names = pattern_generator.fetch_award_names(db_path)

for award_name in award_names:
    input_string = award_name
    file_path = 'web/img/ribbons/' + input_string.replace(" ", "_") + '.png'  # Replace spaces with underscores in file names
    pattern_generator.input_string = input_string  # Update the input string for the pattern generator
    pattern_generator.save_pattern_as_png(file_path)