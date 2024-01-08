import hashlib, random
import numpy as np
from PIL import Image
from matplotlib.colors import to_rgb

class ribbonGenerator:
    def __init__(self, input_string, image_size=(64, 190)):
        self.input_string = input_string
        self.image_size = image_size
        self.hash_string = self._string_to_hash(input_string)
        self.num_blocks = self._determine_number_of_blocks()

    @staticmethod
    def _string_to_hash(input_string):
        """Converts a string to a hash using SHA-256 algorithm."""
        return hashlib.sha256(input_string.encode()).hexdigest()

    def _determine_number_of_blocks(self):
        """Uses the hash to seed a random number generator and determines the number of color blocks."""
        hash_int = int(self.hash_string, 16)
        random.seed(hash_int)
        return random.randint(2, 7)

    def _hash_to_color_and_width_blocks(self):
        """Converts a hash string into color blocks with varying widths. Returns a list of (color, width) tuples."""
        # Ensure we have enough hash data to extract colors and widths
        hash_extended = self.hash_string * ((6 * self.num_blocks) // len(self.hash_string) + 1)
        
        colors = ['#' + hash_extended[i:i+6] for i in range(0, 6 * self.num_blocks, 6)]

        # Randomly distribute widths while ensuring each block is at least 5 pixels wide
        remaining_width = self.image_size[1] - 5 * self.num_blocks
        widths = [15 for _ in range(self.num_blocks)]
        while remaining_width > 0:
            for i in range(self.num_blocks):
                if remaining_width > 0:
                    increment = random.randint(0, remaining_width)
                    widths[i] += increment
                    remaining_width -= increment

        return list(zip(colors, widths))

    def create_variable_width_symmetrical_pattern(self):
        """Creates a pattern with variable number and width of color blocks, determined by the hash."""
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

    def save_pattern_as_png(self, file_path):
        """Saves the generated pattern as a PNG file."""
        pattern_image = self.create_variable_width_symmetrical_pattern()
        Image.fromarray(pattern_image.astype('uint8'), 'RGB').save(file_path)

# Example usage
input_string = 'TOMCAT_TYPE_CONVERSION'
pattern_generator = ribbonGenerator(input_string)
file_path = 'web/img/ribbons/' + input_string + '.png'
pattern_generator.save_pattern_as_png(file_path)
