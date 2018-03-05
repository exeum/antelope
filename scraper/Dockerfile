FROM python

WORKDIR /root
COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT ["./scraper.py"]
