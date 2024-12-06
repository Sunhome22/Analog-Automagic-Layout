#======================================================================================================================#
# Copyright (C) 2024 Bjørn K.T. Solheim, Leidulv Tønnesland
#======================================================================================================================#
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
#======================================================================================================================#

from PIL import Image, ImageDraw, ImageFont


def get_black_white_pixel_boxes_from_image(image_path, scale_factor=3):

    # Open the image
    image = Image.open(image_path)

    if scale_factor != 1:
        new_size = (int(image.size[0] * scale_factor), int(image.size[1] * scale_factor))
        image = image.resize(new_size, Image.NEAREST)  # NEAREST keeps the pixelation sharp

    # Convert the image to grayscale (1-channel) and then to black & white (mode '1')
    image = image.convert('1')

    image_size = image.size
    pixels = image.load()

    black_pixel_boxes = []
    white_pixel_boxes = []

    # Iterate through each pixel in the image
    for y in range(image_size[1]):
        for x in range(image_size[0]):
            if pixels[x, y] == 0:
                black_pixel_boxes.append((x, image_size[1] - y - 1, x + 1, image_size[1] - y))
            else:
                white_pixel_boxes.append((x, image_size[1] - y - 1, x + 1, image_size[1] - y))

    return black_pixel_boxes, white_pixel_boxes


def get_pixel_boxes_from_text(text, font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size=1000):
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"Font not found at {font_path}")
        return None

    image_size = (font_size * len(text), font_size)
    image = Image.new('1', image_size, color=1)  # Black and white image. 1 is white 0 is black

    draw = ImageDraw.Draw(image)
    draw.text((0, 0), text, font=font, fill=0)  # Draws the entire text in black on the image

    pixels = image.load()  # Converts image to pixel data

    pixel_boxes = []
    for y in range(image_size[1]):
        for x in range(image_size[0]):

            if pixels[x, y] == 0:
                # Bounding box for each pixel with flipped y-coordinate
                pixel_boxes.append((x, image_size[1] - y - 1, x + 1, image_size[1] - y))

    return pixel_boxes
