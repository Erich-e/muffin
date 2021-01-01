FROM python:3.9

COPY bootstrap.sh .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
CMD ["./bootstrap.sh"]

