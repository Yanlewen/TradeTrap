import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Rectangle, ConnectionPatch

def zoom_asset_graph():
    # 图片路径
    img_path = "assets/attack_with_fake_news.png"
    # 放大区域（[x1, x2, y1, y2]，单位：像素，需根据实际图片尺寸调整，此处为示例值）
    box = [756, 1158, 313, 783]  
    # 若实际放大效果不对，可通过图像工具（如画图软件）查看准确像素坐标后调整此box
    
    # 读取原图
    img = mpimg.imread(img_path)
    h, w, _ = img.shape

    # 创建画布
    fig = plt.figure(figsize=(12, 8), dpi=300)
    plt.rcParams['font.family'] = 'Times New Roman'

    # 显示完整原图
    left_big, bottom_big, width_big, height_big = 0.05, 0.05, 0.9, 0.9
    ax_big = fig.add_axes([left_big, bottom_big, width_big, height_big])
    ax_big.imshow(img)
    ax_big.axis('off')

    # 在原图上标记放大区域
    x1, x2, y1, y2 = box
    ax_big.plot([x1, x2, x2, x1, x1], [y1, y1, y2, y2, y1], 'r--', linewidth=2)

    # 显示放大区域
    zoomed_img = img[int(y1):int(y2), int(x1):int(x2)]
    left_zoom, bottom_zoom, width_zoom, height_zoom = 0.4, 0.34, 0.35, 0.35
    ax_zoom = fig.add_axes([left_zoom, bottom_zoom, width_zoom, height_zoom])
    ax_zoom.imshow(zoomed_img)
    for spine in ax_zoom.spines.values():
        spine.set_visible(False)
    ax_zoom.set_xticks([])
    ax_zoom.set_yticks([])
    rect = Rectangle(
        (0, 0), 1, 1,
        transform=ax_zoom.transAxes,
        fill=False,
        edgecolor='red',
        linewidth=3,
        linestyle='--'
    )
    ax_zoom.add_patch(rect)
    ax_zoom.set_title('Early Information Gap', fontsize=12, color='#ffd966')

    connectors = [
        ConnectionPatch(
            xyA=(x2, y1),
            xyB=(0, 1),
            coordsA='data',
            coordsB='axes fraction',
            axesA=ax_big,
            axesB=ax_zoom,
            color='red',
            linewidth=2,
            linestyle='--'
        ),
        ConnectionPatch(
            xyA=(x2, y2),
            xyB=(0, 0),
            coordsA='data',
            coordsB='axes fraction',
            axesA=ax_big,
            axesB=ax_zoom,
            color='red',
            linewidth=2,
            linestyle='--'
        )
    ]
    for conn in connectors:
        fig.add_artist(conn)

    plt.savefig(
        'assets/zoomed_asset_graph_with_fake_news.png',
        bbox_inches='tight',  # 裁剪到内容边界
        pad_inches=0,         # 边界与内容的距离设为0
        dpi=300               # 保持高清
    )
    plt.show()

zoom_asset_graph()