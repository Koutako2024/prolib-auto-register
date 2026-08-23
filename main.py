import cv2, asyncio
from os import listdir
from pathlib import Path
from sys import argv
from typing import Any
from zxingcpp import read_barcodes
from httpx import AsyncClient


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


def read_barcode(filename: str | Path) -> str | None:
    img = cv2.imread(filename)
    if img is None:
        raise ValueError(filename)
    results = read_barcodes(img)
    return min(results, key=lambda r: r.position.top_left.y).text if results else None


async def fetch_book_data(isbn: str) -> Any:
    async with AsyncClient() as client:
        response = await client.get(f"https://api.openbd.jp/v1/get?isbn={isbn}")
    return response.json()


async def fetch_summary(
    isbn: str,
) -> tuple[str | None, str | None, str | None, str | None]:
    "->(title, publisher, pubdate, author)"
    data = await fetch_book_data(isbn)
    try:
        hoge: dict[str, str | None] = data[0]["summary"]
    except Exception as e:
        print(f"error: no data in DB. {e=}, {isbn=}, {data=}")
        return None, None, None, None
    title = hoge.get("title")
    publisher = hoge.get("publisher")
    pubdate = hoge.get("pubdate")
    author = hoge.get("author")
    return title, publisher, pubdate, author


def get_authors(raw: str) -> list[str]:
    """
    "Brown,Alice 村山,公保,1967- 久留米高専プログラミングラボ部 権田原言／監修 ほか"
      -> ["Alice Brown", "村山公保", "久留米高専プログラミングラボ部", "権田原言"]
    """
    authors = raw.split(" ")
    shift: int = 0
    for i in range(len(authors)):
        splited_by_slash = authors[i + shift].split("／")
        if len(splited_by_slash) > 1:
            authors[i + shift] = "／".join(splited_by_slash[:-1])

        if authors[i + shift] == "ほか":
            del authors[i + shift]
            shift -= 1
            continue

        splited_by_comma = authors[i + shift].split(",")
        match len(splited_by_comma):
            case 0:
                del authors[i + shift]
                shift -= 1
            case 1:
                authors[i + shift] = splited_by_comma[0]
            case _:
                left, right, *_ = splited_by_comma
                if left[0].isascii():
                    authors[i + shift] = right + " " + left
                else:
                    authors[i + shift] = left + right
    return authors


async def proc(dir: Path, no_suf: str, exntensions: list[str]) -> None:
    try:
        path = dir / (no_suf + "_2." + exntensions[1])
        isbn = read_barcode(path)
        if isbn is None:
            print(f"error: couldn't read barcode. {path=}")
            return
        title, publisher, pubdate, author = await fetch_summary(isbn)
        if title is None:
            print("error: title is None.")
            return

        json: dict = {
            "contents": "TODO",
            "tags": ["TODO", "auto-registered"],
            "title": title,
            "authors": get_authors(author) if author else None,
            "publisher": publisher,
            "publishYear": int(pubdate[:4]) if pubdate else None,
            "holdingNum": 1,
            "isbn": isbn,
            "coverImageUrl": None,
            "backCoverImageUrl": None,
            "spineImageUrl": None,
        }
        print(f"{json=}")
        return
        async with AsyncClient() as client:
            response = await client.post(
                "https://prolib.prolab.club/api/books/", json=json
            )
        print(f"{response.status_code=}")
        print(f"{response.text=}")
    except Exception as e:
        print(e)
    return


async def main() -> None:
    print("started.")

    if len(argv) < 2:
        target_dir = Path(input("target dir: "))
    else:
        target_dir = Path(argv[1])

    filenames = listdir(target_dir)
    data: dict[str, list[str]] = dict()  # dict[no_suf, list[extension]]
    for s in filenames:
        print(f"{s=}")
        extension = "".join(s.split(".")[-1])
        underbar_splited = s.split("_")
        no = int(underbar_splited[-1][0])
        no_suf = "".join(underbar_splited[:-1])
        if no_suf not in data:
            data[no_suf] = ["?", "?", "?"]
        data[no_suf][no - 1] = extension

    print(data)
    input("enter to proceed: ")

    tasks = [proc(target_dir, k, v) for k, v in data.items()]
    await asyncio.gather(*tasks)
    print("finished.")
    return


if __name__ == "__main__":
    asyncio.run(main())
