FROM python:3.10

RUN apt update && apt install -y ffmpeg

WORKDIR /app
COPY . .

RUN pip install -r gereksinimler.txt

CMD ["python", "bot.py"]
