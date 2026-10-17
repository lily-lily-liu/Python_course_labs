import numpy as np
import matplotlib.pyplot as plt

# 全局配置：解决中文和负号显示异常
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False

def monte_carlo_pentagram(total_points: int = 50000, star_radius: float = 1.0):
    """
    蒙特卡罗方法生成完整五芒星图形
    :param total_points: 随机采样总点数，点数越多图形越清晰、误差越小
    :param star_radius: 五芒星外接圆半径
    """
    # 1. 生成正方形范围内的均匀随机点，范围略大于五芒星外接圆避免边缘裁剪
    x = np.random.uniform(-star_radius * 1.3, star_radius * 1.3, total_points)
    y = np.random.uniform(-star_radius * 1.3, star_radius * 1.3, total_points)

    # 2. 转换为极坐标，生成五芒星边界函数
    r = np.sqrt(x ** 2 + y ** 2)
    theta = np.arctan2(y, x)
    # 标准五芒星极坐标隐函数，自动生成尖锐的星形顶点
    pentagram_boundary = star_radius * (0.6 + 0.4 * np.cos(5 * theta))
    # 额外加一个边界裁剪，避免超出外接圆的部分溢出
    pentagram_boundary[pentagram_boundary < 0] = 0

    # 3. 蒙特卡罗判定：点到原点距离小于边界值则判定为落在五芒星内部
    inside_star = r <= pentagram_boundary

    # 4. 计算五芒星理论真实面积、蒙特卡罗估算面积
    outer_square_area = (2 * star_radius * 1.3) ** 2
    theoretical_star_area = (5 / 2) * (star_radius ** 2) * np.sin(72 * np.pi / 180)
    estimated_star_area = np.sum(inside_star) / total_points * outer_square_area
    relative_error = abs(estimated_star_area - theoretical_star_area) / theoretical_star_area * 100

    # 5. 控制台输出统计结果
    print("="*40)
    print(f"蒙特卡罗五芒星实验结果")
    print(f"总采样点数: {total_points}")
    print(f"五芒星外接圆半径: {star_radius}")
    print(f"理论真实面积: {theoretical_star_area:.6f}")
    print(f"蒙特卡罗估算面积: {estimated_star_area:.6f}")
    print(f"面积相对误差: {relative_error:.3f}%")
    print("="*40)

    # 6. 绘制最终图形
    plt.figure(figsize=(8, 8), dpi=100)
    # 五芒星内部点使用金色，外部点用浅灰色填充背景
    plt.scatter(x[inside_star], y[inside_star], color="#FFD700", s=2.5, label="五芒星内部点")
    plt.scatter(x[~inside_star], y[~inside_star], color="#F5F5F5", s=0.8, alpha=0.3)
    # 添加理论参考外接圆，辅助观察顶点对齐度
    circle_theta = np.linspace(0, 2*np.pi, 200)
    plt.plot(star_radius*np.cos(circle_theta), star_radius*np.sin(circle_theta),
             color="darkred", linestyle="--", linewidth=1.2, alpha=0.7, label="五芒星外接参考圆")

    # 图形样式优化
    plt.title(f"蒙特卡罗手搓五芒星 | 采样点数: {total_points}", fontsize=15, pad=18)
    plt.xlabel("X 坐标", fontsize=11)
    plt.ylabel("Y 坐标", fontsize=11)
    plt.axis("equal")
    plt.xlim(-star_radius*1.4, star_radius*1.4)
    plt.ylim(-star_radius*1.4, star_radius*1.4)
    plt.legend(loc="upper right")
    plt.grid(linestyle=":", alpha=0.4)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    monte_carlo_pentagram(total_points=60000)
