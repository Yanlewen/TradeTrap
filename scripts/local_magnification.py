import matplotlib.pyplot as plt
import matplotlib.image as mpimg

def zoom_asset_graph():
    img_path = "assets/image.png"
    box = [925, 1127, 344, 752]  # 替换为实际像素坐标
    
    img = mpimg.imread(img_path)
    h, w, _ = img.shape  # 获取原图宽高
    
    # 配置画布：宽高比与原图一致，无内边距
    fig = plt.figure(figsize=(w/100, h/100), dpi=100)
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['figure.autolayout'] = False
    plt.rcParams['axes.edgecolor'] = 'none'
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
    
    # 显示原图
    ax_big = fig.add_axes([0, 0, 1, 1])
    ax_big.imshow(img)
    ax_big.axis('off')
    
    # 标记放大区域
    x1, x2, y1, y2 = box
    ax_big.plot([x1, x2, x2, x1, x1], [y1, y1, y2, y2, y1], 'r--', linewidth=2)
    
    # 显示放大图（中间位置）
    zoomed_img = img[int(y1):int(y2), int(x1):int(x2)]
    ax_zoom = fig.add_axes([0.4, 0.4, 0.35, 0.35])
    ax_zoom.imshow(zoomed_img)
    ax_zoom.axis('off')
    ax_zoom.set_title('Early Information Gap', fontsize=12)
    
    # 保存时强制无白边
    plt.savefig(
        'assets/zoomed_asset_graph.png',
        bbox_inches='tight',
        pad_inches=0,
        dpi=300
    )
    plt.show()

zoom_asset_graph()