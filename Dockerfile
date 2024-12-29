FROM python:3.12-slim AS builder

WORKDIR /app 

COPY ./requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt 

FROM python:3.12-alpine3.20 AS runner

WORKDIR /app 

RUN pip install gunicorn 

COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

COPY ./wsgi.py /app/  

COPY ./app.py /app/

COPY ./templates/index.html /app/templates/index.html

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
