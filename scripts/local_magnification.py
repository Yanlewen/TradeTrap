import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Rectangle, ConnectionPatch
import matplotlib.colors as mcolors
import numpy as np

TARGET_LINE_COLORS = [
    "#3480b8",  # blue
    "#f5cb5c",  # yellow
    "#c82423",  # red
]


def _add_glow_border(
    ax,
    color: str = "3D9F3C",
    core_linewidth: float = 3.0,
    glow_spread: float = 6.0,
    glow_layers: int = 4,
    alpha_decay: float = 0.35,
):
    """在给定坐标轴（0-1 范围）内绘制带渐变发光效果的矩形边框。"""

    rgb = mcolors.to_rgb(color)
    for layer in range(glow_layers, 0, -1):
        ratio = layer / glow_layers
        lw = core_linewidth + glow_spread * ratio
        alpha = max(0.0, alpha_decay * ratio)
        rect = Rectangle(
            (0, 0),
            1,
            1,
            transform=ax.transAxes,
            fill=False,
            edgecolor=(*rgb, alpha),
            linewidth=lw,
            linestyle="--",
            zorder=1,
        )
        ax.add_patch(rect)

    rect_core = Rectangle(
        (0, 0),
        1,
        1,
        transform=ax.transAxes,
        fill=False,
        edgecolor=color,
        linewidth=core_linewidth,
        linestyle="--",
        zorder=2,
    )
    ax.add_patch(rect_core)


def _gaussian_blur(mask: np.ndarray, sigma: float) -> np.ndarray:
    """对二维数组执行 separable Gaussian blur（无需额外依赖）。"""

    if sigma <= 0:
        return mask

    radius = max(1, int(3 * sigma))
    ax = np.arange(-radius, radius + 1, dtype=np.float32)
    kernel = np.exp(-(ax ** 2) / (2 * sigma ** 2))
    kernel /= kernel.sum()

    blurred = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), axis=0, arr=mask)
    blurred = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), axis=1, arr=blurred)
    return blurred


def _dilate_mask(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    """简单的八邻域膨胀，用于加粗线条。"""

    mask = mask.astype(np.uint8)
    for _ in range(max(iterations, 0)):
        padded = np.pad(mask, 1, mode="constant")
        neighbors = [
            padded[1:-1, 1:-1],
            padded[:-2, 1:-1],
            padded[2:, 1:-1],
            padded[1:-1, :-2],
            padded[1:-1, 2:],
            padded[:-2, :-2],
            padded[:-2, 2:],
            padded[2:, :-2],
            padded[2:, 2:],
        ]
        mask = np.maximum.reduce(neighbors)
    return mask.astype(bool)


def _enhance_zoom_lines(
    zoom_img: np.ndarray,
    target_colors: list[str] = TARGET_LINE_COLORS,
    hue_threshold: float = 0.015,
    sat_threshold: float = 0.25,
    val_threshold: float = 0.35,
    dilation_passes: int = 3,
    blend_factor: float = 0.15,
) -> np.ndarray:
    """针对放大区域中的曲线加粗，尽可能保持原有色调。"""

    if zoom_img.ndim != 3 or zoom_img.shape[2] < 3:
        return zoom_img

    arr = zoom_img.astype(np.float32)
    orig_dtype = zoom_img.dtype

    needs_rescale = arr.max() > 1.5
    if needs_rescale:
        arr /= 255.0

    rgb = arr[..., :3].clip(0.0, 1.0)
    hsv = mcolors.rgb_to_hsv(rgb)
    value_channel = hsv[..., 2]
    saturation_channel = hsv[..., 1]

    for color_hex in target_colors:
        target_rgb = np.array(mcolors.to_rgb(color_hex), dtype=np.float32)
        target_hsv = mcolors.rgb_to_hsv(target_rgb.reshape(1, 1, 3))[0, 0]

        hue_diff = np.abs(hsv[..., 0] - target_hsv[0])
        hue_diff = np.minimum(hue_diff, 1.0 - hue_diff)
        mask = (
            (hue_diff < hue_threshold)
            & (saturation_channel > sat_threshold)
            & (value_channel > val_threshold)
        )
        if not np.any(mask):
            continue

        dilated = _dilate_mask(mask, iterations=dilation_passes)
        edge_mask = dilated & ~mask

        for channel in range(3):
            channel_data = rgb[..., channel]
            channel_data[edge_mask] = (
                channel_data[edge_mask] * (1 - blend_factor)
                + target_rgb[channel] * blend_factor
            )
            channel_data[mask] = (
                channel_data[mask] * (1 - blend_factor / 2)
                + target_rgb[channel] * (blend_factor / 2)
            )
            rgb[..., channel] = channel_data

        if arr.shape[2] == 4:
            alpha_channel = arr[..., 3]
            alpha_channel[dilated] = np.clip(alpha_channel[dilated], 0.8, 1.0)
            arr[..., 3] = alpha_channel

    result = np.clip(rgb, 0.0, 1.0)

    if arr.shape[2] == 4:
        alpha_channel = np.clip(arr[..., 3], 0.0, 1.0)
        combined = np.zeros_like(arr)
        combined[..., :3] = result
        combined[..., 3] = alpha_channel
    else:
        combined = result

    if orig_dtype == np.uint8 or needs_rescale:
        combined = (combined * 255.0).round().astype(np.uint8)
    elif np.issubdtype(orig_dtype, np.floating):
        combined = combined.astype(orig_dtype)

    return combined


def zoom_asset_graph():
    # 图片路径
    img_path = "assets/attack_with_reverse_expectations.png"
    # 放大区域（[x1, x2, y1, y2]，单位：像素，需根据实际图片尺寸调整，此处为示例值）
    box = [391, 549, 157, 380]  
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
    ax_big.plot(
        [x1, x2, x2, x1, x1],
        [y1, y1, y2, y2, y1],
        color="#3D9F3C",
        linestyle="--",
        linewidth=3,
    )

    # 显示放大区域
    zoomed_img = img[int(y1):int(y2), int(x1):int(x2)]
    left_zoom, bottom_zoom, width_zoom, height_zoom = 0.42, 0.34, 0.35, 0.35
    zoomed_img = _enhance_zoom_lines(zoomed_img)
    ax_zoom = fig.add_axes([left_zoom, bottom_zoom, width_zoom, height_zoom])
    ax_zoom.imshow(zoomed_img)
    for spine in ax_zoom.spines.values():
        spine.set_visible(False)
    ax_zoom.set_xticks([])
    ax_zoom.set_yticks([])
    rect = Rectangle(
        (0, 0),
        1,
        1,
        transform=ax_zoom.transAxes,
        fill=False,
        edgecolor='#3D9F3C',
        linewidth=5,
        linestyle='--',
        zorder=5,
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
            color='#3D9F3C',
            linewidth=3,
            linestyle='--'
        ),
        ConnectionPatch(
            xyA=(x2, y2),
            xyB=(0, 0),
            coordsA='data',
            coordsB='axes fraction',
            axesA=ax_big,
            axesB=ax_zoom,
            color='#3D9F3C',
            linewidth=3,
            linestyle='--'
        )
    ]
    for conn in connectors:
        fig.add_artist(conn)

    plt.savefig(
        'assets/zoomed_attack_with_reverse_expectations1.png',
        bbox_inches='tight',  # 裁剪到内容边界
        pad_inches=0,         # 边界与内容的距离设为0
        dpi=300               # 保持高清
    )
    plt.show()

zoom_asset_graph()