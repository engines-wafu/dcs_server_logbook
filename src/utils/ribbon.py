import hashlib, random, sqlite3
import numpy as np
from PIL import Image
from matplotlib.colors import to_rgb

class ribbonGenerator:
    def __init__(self, input_string, image_size=(64, 190), color_array=None, min_block_width_percent=5, max_block_width_percent=20):
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
        return random.randint(2, 4)

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
  "#DAA520", 
  "#C0C0C0", 
  "#CD7F32", 
  "#B9CCED", 
  "#800000", 
  "#008000", 
  "#000080", 
  "#FFD700", 
  "#A52A2A", 
  "#FFA500", 
  "#4682B4", 
  "#6B8E23"
]

db_path = 'data/db/mayfly.db'

# Initialize the pattern generator
pattern_generator = ribbonGenerator(
    "example string",
    color_array=predefined_colors,
    min_block_width_percent=5,
    max_block_width_percent=40
)

# Fetch award names using the instance of the pattern generator
award_names = pattern_generator.fetch_award_names(db_path)

for award_name in award_names:
    input_string = award_name
    file_path = 'web/img/ribbons/' + input_string.replace(" ", "_") + '.png'  # Replace spaces with underscores in file names
    pattern_generator.input_string = input_string  # Update the input string for the pattern generator
    pattern_generator.save_pattern_as_png(file_path)