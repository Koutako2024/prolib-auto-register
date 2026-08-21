import cv2, zxingcpp


def shikakukeitoridasu() -> None:
    img = cv2.imread("input.jpg")
    if img is None:
        raise Exception("Image not found!")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    max_area = 0
    best_quad = None
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > max_area:
                max_area = area
                best_quad = approx
    if best_quad is not None:
        x, y, w, h = cv2.boundingRect(best_quad)
        cropped = img[y : y + h, x : x + w]
    cv2.imwrite("cropped.jpg", cropped)
    return


def read_barcode() -> str:
    img = cv2.imread("warped.jpg")
    results = zxingcpp.read_barcodes(img)
    return min(results, key=lambda r: r.position.top_left.y).text


def main() -> None:
    print("started.")
    print(read_barcode())
    return


if __name__ == "__main__":
    main()
