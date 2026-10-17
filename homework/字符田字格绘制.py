def draw_tianzige(rows_per_cell=3, cols_per_cell=3):
    """
    绘制字符田字格
    :param rows_per_cell: 每个小格子的行数（建议≥2）
    :param cols_per_cell: 每个小格子的列数（建议≥2）
    """
    total_rows = 2 * rows_per_cell + 1
    total_cols = 2 * cols_per_cell + 1
    mid_row = rows_per_cell
    mid_col = cols_per_cell

    for i in range(total_rows):
        if i == 0 or i == mid_row or i == total_rows - 1:
            # 绘制横线行
            line = []
            for j in range(total_cols):
                line.append('+' if j == 0 or j == mid_col or j == total_cols - 1 else '-')
            print(''.join(line))
        else:
            # 绘制竖线行
            line = []
            for j in range(total_cols):
                line.append('|' if j == 0 or j == mid_col or j == total_cols - 1 else ' ')
            print(''.join(line))

# 示例调用
draw_tianzige(2, 3)
