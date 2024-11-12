FROM python:3.8.10

ADD . /app

WORKDIR /app

RUN pip install -r requirements.txt

CMD ["python", "RFES_Control_Center_v2.py"]

