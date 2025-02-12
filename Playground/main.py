from PIL import Image, ImageDraw, ImageFont


def create_knitting_pattern(pattern, cell_size=20, add_row_numbers=False):
    """
    Создает изображение схемы для вязания на основе двумерного массива.

    :param pattern: Двумерный массив (список списков) с данными о схеме.
    :param cell_size: Размер одной ячейки (петли) в пикселях.
    :param add_row_numbers: Если True, добавляет номера рядов слева.
    :return: Изображение (объект PIL.Image).
    """
    rows = len(pattern)
    cols = len(pattern[0])

    # Определяем размер изображения
    width = cols * cell_size + (50 if add_row_numbers else 0)
    height = rows * cell_size
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()  # Используем стандартный шрифт

    # Рисуем номера рядов (если нужно)
    if add_row_numbers:
        for i in range(rows):
            draw.text((5, i * cell_size + 5), str(rows - i), fill='black', font=font)

    # Рисуем сетку и заполняем её на основе массива
    for i in range(rows):
        for j in range(cols):
            # Определяем цвет и текст на основе значения в массиве
            if isinstance(pattern[i][j], int):
                color = 'black' if pattern[i][j] == 1 else 'white'
                text = ''
            else:
                if pattern[i][j] == 'K':
                    color = 'black'
                    text = 'K'
                elif pattern[i][j] == 'P':
                    color = 'white'
                    text = 'P'
                else:
                    color = 'gray'
                    text = ''

            # Рисуем прямоугольник (ячейку)
            x_offset = 50 if add_row_numbers else 0
            draw.rectangle(
                [x_offset + j * cell_size, i * cell_size, x_offset + (j + 1) * cell_size, (i + 1) * cell_size],
                fill=color,
                outline='gray'
            )
            # Добавляем текст (символ петли)
            if text:
                draw.text(
                    (x_offset + j * cell_size + 5, i * cell_size + 5),
                    text,
                    fill='black' if color == 'white' else 'white',
                    font=font
                )
    return img


# Пример использования
pattern = [
    [0, 1, 0, 1, 1],
    [1, 0, 1, 0, 1],
    [0, 1, 0, 1, 0],
    [1, 0, 1, 0, 1]
]

# Создаем изображение с номерами рядов
img = create_knitting_pattern(pattern, cell_size=20, add_row_numbers=True)
img.save('knitting_pattern_with_row_numbers.png')
img.show()

# Пример с использованием символов для петель
pattern_with_stitches = [
    ['K', 'P', 'K', 'P', 'a'],
    ['P', 'K', 'P', 'K', 'P'],
    ['K', 'P', 'K', 'P', 'K'],
    ['P', 'K', 'P', 'K', 'P']
]

img_with_stitches = create_knitting_pattern(pattern_with_stitches, cell_size=20, add_row_numbers=True)
img_with_stitches.save('knitting_pattern_with_stitches.png')
img_with_stitches.show()