import httpx
import asyncio
from string import ascii_uppercase
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import json
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("API_KEY")

client = genai.Client(api_key=api_key)
URL = "https://naurok.com.ua/test-beta/api/session/"

MAX_TOKENS = 1000

IMG_MARK = "[зображення]"

def clean(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all("sup"):
        t.replace_with("^(" + t.get_text() + ")")
    for t in soup.find_all("sub"):
        t.replace_with("_(" + t.get_text() + ")")
    for t in soup.find_all("img"):
        t.replace_with(IMG_MARK)
    return soup.get_text(strip=True)

def get_image(item):
    url = item.get("image")
    if isinstance(url, str) and url.strip():
        return url.strip()
    return None

def with_marker(item, key):
    text = clean(item[key])
    if get_image(item) and IMG_MARK not in text:
        text += IMG_MARK
    return text

async def fetch_image(http, url):
    r = await http.get(url, follow_redirects=True)
    r.raise_for_status()
    mime = r.headers.get("content-type", "image/png").split(";")[0]
    return r.content, mime

async def collect_images(http, questions):
    jobs = []
    for i, q in enumerate(questions, start=1):
        if url := get_image(q):
            jobs.append((f"Зображення до питання {i}", url))
        for letter, opt in zip(ascii_uppercase, q["options"]):
            if url := get_image(opt):
                jobs.append((f"Зображення до питання {i}, варіанту {letter}", url))

    results = await asyncio.gather(
        *(fetch_image(http, url) for _, url in jobs),
        return_exceptions=True,
    )

    images = []
    for (label, url), res in zip(jobs, results):
        if isinstance(res, Exception):
            print(f"error pizdec {url}: {res}")
        else:
            images.append((label, *res))
    return images

def build_prompt(questions):
    parts = []
    for i, question in enumerate(questions, start=1):
        text = with_marker(question, 'content')
        options = "\n".join(
            f"{l}) {with_marker(op, 'value')}"
            for l, op in zip(ascii_uppercase, question["options"])
        )
        parts.append(f"{i}. {text}\n{options}")
    return "\n\n".join(parts)

async def solve(questions, subject, grade, images):
    prompt = (
        f"Предмет: {subject}, {grade}.\n"
        "Розв'яжи кожне завдання. Для кожного поверни об'єкт з полями "
        '"reasoning" (коротке розв\'язання) і ПОТІМ "answer" (масив літер). '
        'Приклад: {"1": {"reasoning": "...", "answer": ["B"]}, '
        '"2": {"reasoning": "...", "answer": ["C", "A"]}}\n'
        f"Позначка {IMG_MARK} означає, що до питання додано картинку; "
        "усі картинки йдуть нижче з підписами.\n"
        "Поверни тільки JSON.\n\n"
        + build_prompt(questions)
    )
    contents = [prompt]
    for label, data, mime in images:
        contents.append(label + ":")
        contents.append(types.Part.from_bytes(data=data, mime_type=mime))
    resp = await client.aio.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type="application/json"), # , max_output_tokens=MAX_TOKENS
    )
    print("Токенов спиздило: ", resp.usage_metadata.prompt_token_count)
    text = resp.text
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Модель вернула кривой json: {text[:200]}") from e

async def main():
    uuid = input("Введите uuid: ").split('/')[-1]
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(URL, follow_redirects=True, params={"uuid": uuid})
        if r.status_code == 404:
            print("Некорректная ссылка", r.status_code)
            return
        data = r.json()
        questions = data["questions"]
        images = await collect_images(client, questions)

    print(f"Название теста: {data["document"]["name"]}, {data["document"]["subject"]}, {data["document"]["grade"]}")
    print(f"Картинок найдено: {len(images)}")

    answers = await solve(questions, data["document"]["subject"], data["document"]["grade"], images)
    for num, item in answers.items():
        q = questions[int(num)-1]
        for letter in item["answer"]:
            idx = ord(letter) - ord('A')
            print(f"{num}. {letter} — {clean(q['options'][idx]['value'])}")

if __name__ == '__main__':
    asyncio.run(main())