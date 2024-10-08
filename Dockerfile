FROM python:3.9-slim
WORKDIR /app
RUN pip install flask
RUN pip install jsonschema
RUN pip install requests
RUN pip install pymongo
COPY book-club-API.py .
EXPOSE 5001
CMD ["python3", "book-club-API.py"] 
