import httpx
import asyncio
from string import ascii_uppercase
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import json
from config import API_KEY

client = genai.Client(api_key=API_KEY)
URL = "https://naurok.com.ua/test-beta/api/session/"

MAX_TOKENS = 1000
MODEL = "gemini-3.5-flash-lite"

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
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type="application/json"), # , max_output_tokens=MAX_TOKENS
    )
    print("Токенов спиздило: ", resp.usage_metadata.prompt_token_count)
    text = resp.text
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Модель вернула кривой json: {text[:200]}") from e

async def main(url: str):
    uuid = url.split('/')[-1]
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(URL, follow_redirects=True, params={"uuid": uuid})
        r.raise_for_status()
        if r.status_code == 404:
            return (
                "❌ <b>Некорректная ссылка!</b>\n\n"
                "⚠️ <b>Важно!</b>\n"
                "Отправляйте ссылку непосредственно во время прохождения теста."
            )
        data = r.json()
        questions = data["questions"]
        images = await collect_images(client, questions)

    result = (
        f"📋 <b>{data['document']['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📚 Предмет: <b>{data['document']['subject']}</b>\n"
        f"🎓 Класс: <b>{data['document']['grade']}</b>\n"
        f"🖼 Изображений найдено: <b>{len(images)}</b>\n\n"
        f"✅ <b>Ответы:</b>\n"
    )

    answers = await solve(questions, data["document"]["subject"], data["document"]["grade"], images)

    for num, item in answers.items():
        q = questions[int(num) - 1]
        result += f"\n<b>{num}.</b>\n"
        for letter in item["answer"]:
            idx = ord(letter) - ord('A')
            option = clean(q['options'][idx]['value'])
            result += f"   <b>{letter})</b> {option}\n"

    result += "\n━━━━━━━━━━━━━━━━━━\n"
    result += f"🤖 <i>Ответы сгенерированы {MODEL}</i>"

    return result

if __name__ == '__main__':
    url = input("Введите url: ")
    print(asyncio.run(main(url)))