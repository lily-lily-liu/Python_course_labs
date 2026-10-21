import turtle as t


def koch(size, n):
    """递归绘制n阶科赫曲线，size为线段总长度"""
    if n == 0:
        t.fd(size)
    else:
        for angle in [0, 60, -120, 60]:
            t.left(angle)
            koch(size / 3, n - 1)


def main(order):
    """绘制指定阶数的科赫雪花"""
    # 窗口大小适配高阶雪花，避免图形超出边界
    t.setup(800, 800)
    t.speed(0)  # 0为最快绘制速度，数字1-10速度递增
    t.penup()
    t.goto(-250, 120)  # 调整初始位置让雪花居中
    t.pendown()
    t.pensize(2)
    t.pencolor("blue")

    # 等边三角形的三条边，每条边绘制科赫曲线
    for i in range(3):
        koch(500, order)
        t.right(120)  # 每条曲线结束后右转120度，拼接成闭合雪花

    t.hideturtle()
    t.done()

if __name__ == '__main__':
    draw_order = 4  # 可修改为0、1、2、3、4
    main(draw_order)

# 阶数	图形特征
# 0阶	普通等边三角形
# 1阶	三角形每条边被替换为标准1阶科赫曲线，边缘出现3个小凸起
# 2阶	每个小线段再次生成科赫结构，锯齿细节明显增加
# 3阶	经典的科赫雪花形态，分形特征清晰可辨
# 4阶	细节非常丰富，边缘呈现密集的自相似分形纹理
