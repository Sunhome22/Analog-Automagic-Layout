from PIL import Image, ImageDraw, ImageFont


def get_text_pixel_boxes(text, font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size=1000):
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


