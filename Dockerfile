FROM python:3.12

WORKDIR /src

COPY requirements.txt .

RUN pip3 install --upgrade pip
RUN pip3 install --default-timeout=1000 --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH /src

CMD ["python", "src/app/bot.py"]
