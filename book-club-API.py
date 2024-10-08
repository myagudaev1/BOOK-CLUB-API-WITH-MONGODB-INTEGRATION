from flask import Flask, jsonify, request
import requests
from jsonschema import validate
import re
from pymongo import MongoClient
from pymongo.collection import ReturnDocument

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient('mongodb://mongo:27017')
db = client['book_api_db']  # database for the books api
books_collection = db['books']
ratings_collection = db['ratings']
counter_collection = db['counter']
counter_collection.insert_one({"counterID": 1}) # counter to keep track of id assignment

accepted_genres = ['Fiction', 'Children', 'Biography', 'Science', 'Science Fiction', 'Fantasy', 'Other']

# json schema for the book json objects
book_schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "authors": {"type": "string"},
        "ISBN": {"type": "string"},
        "publisher": {"type": "string"},
        "publishedDate": {"type": "string"},
        "genre": {"type": "string"}
    },
    "required": ["title", "authors", "ISBN", "publisher", "publishedDate", "genre"]
}
# json schema for the json object sent with a post book request
book_post_schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "ISBN": {"type": "string"},
        "genre": {"type": "string"}
    },
    "required": ["title", "ISBN", "genre"]
}
# json schema for the json object sent with a post rating request
rating_post_schema = {
    "type": "object",
    "properties": {
        "value": {"type": "number"}
    },
    "required": ["value"]
}
# regex patterns for the publishedDate
date_pattern = r"\d{4}-\d{2}-\d{2}"
year_pattern = r"\d{4}"

def invoke_google_books_API(ISBN: str):
    try:
        # Make a request to Google books API to get additional information
        google_books_url = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{ISBN}'
        response = requests.get(google_books_url)
        try:
            google_books_data = response.json()['items'][0]['volumeInfo']
            # retrieve the fields from the response, or set as "missing" by default if none found
            return google_books_data.get("authors", "missing"), google_books_data.get("publisher", "missing"), google_books_data.get("publishedDate", "missing")
        except:
            # If the google api finds no results for the ISBN number, we take that as an invalid ISBN number
            if response.json()['totalItems'] == 0 or response.json() == {}:
                return jsonify("Error: Invalid ISBN number."), 400
    except:
        return jsonify("Error: Internal server error."), 500

@app.get('/books')
def get_books():
    # we create a dictionary of the arguments  of the request query
    queryStringDict = request.args
    books = books_collection.find({}, {"_id": 0})
    filtered_books = list(books)
    for key in queryStringDict:
        filtered_books = [book for book in filtered_books if book[key] == queryStringDict[key]]
    return jsonify(filtered_books), 200

@app.get('/ratings/<id>')
def get_ratings_with_id(id):
    rating = ratings_collection.find_one({'id': id}, {"_id": 0})
    if rating:
        return jsonify(rating), 200
    # If no book found with the given ID, return an error message
    return jsonify("Error: Book not found."), 404

@app.get('/ratings')
def get_ratings():
    queryStringDict = request.args
    if len(queryStringDict) > 1 or (len(queryStringDict) == 1 and 'id' not in queryStringDict):
        return jsonify("Error: Queries can only be of the form id=<string>."), 422
    elif len(queryStringDict) == 1:
        id = queryStringDict['id']
        rating = ratings_collection.find_one({'id': id}, {"_id": 0})
        if rating:
            return jsonify(rating), 200
        # If no book found with the given ID, return an error message
        return jsonify("Error: Book not found."), 404
    else:
        ratings_list = list(ratings_collection.find({}, {"_id": 0}))
        return jsonify(ratings_list), 200

@app.get('/books/<id>')
def get_book_with_id(id):
    book = books_collection.find_one({'id': id}, {"_id": 0})
    if book:
        return jsonify(book), 200
    # If no book found with the given ID, return an error message
    return jsonify("Error: Book not found."), 404

@app.put('/books/<id>')
def put_book_with_id(id):
    if request.is_json:
        book = books_collection.find_one({'id': id})
        if book:
            data = request.json
            try:
                validate(instance=data, schema=book_schema)
            except:
                return jsonify("Error: Missing, incorrectly-spelled or extra fields."), 422
            rating = ratings_collection.find_one({'id': id})
            books_collection.update_one({'id': id}, {'$set': data})
            if rating:
                ratings_collection.update_one({'id': id}, {'$set': {'title': data['title']}})
            return jsonify({'ID': id}), 200
        # If no book found with the given ID, return an error message
        return jsonify("Error: Book not found."), 404
    else:
        return jsonify("Error: Unsupported media type. JSON expected."), 415
        

@app.delete('/books/<id>')
def delete_book_with_id(id):
    book = books_collection.find_one({'id': id})
    if book:
        books_collection.delete_one({'id': id})
        rating = ratings_collection.find_one({'id': id})
        if rating:
            ratings_collection.delete_one({'id': id})
            return jsonify({'ID': id}), 200

    # If no book found with the given ID, return an error message
    return jsonify("Error: Book not found"), 404

@app.post('/books')
def post_book():
    if request.is_json:
        # Create a book record
        data = request.json
        try:
            validate(instance=data, schema=book_post_schema)
        except:
            return jsonify("Error: Missing, incorrectly-spelled or extra fields."), 422
        genre = data.get('genre')
        if genre not in accepted_genres:
            return jsonify("Error: Not an acceptable genre."), 422
        ISBN = data.get('ISBN')
        book = books_collection.find_one({'ISBN': ISBN})
        if book:
            return jsonify("Error: Book with this ISBN number already exists."), 422
        
        title = data.get('title')
        try:
            authors, publisher, publishedDate = invoke_google_books_API(ISBN)
        except:
            return invoke_google_books_API(ISBN)

        if authors != "missing":
            formatted_authors = authors[0]
            for i in range(1, len(authors)):
                formatted_authors += ' and ' + ''.join(authors[i])
        else:
            formatted_authors = authors
        
        if not (re.fullmatch(date_pattern, publishedDate) or re.fullmatch(year_pattern, publishedDate)):
            publishedDate = "missing"
        
        id = str(counter_collection.find_one_and_update(
        {},  # Find the first document in the collection (assuming only one counter exists)
        {"$inc": {"counterID": 1}},  # Increment the counterID by 1
        return_document=ReturnDocument.BEFORE)["counterID"])

        book = {
            "title": title,
            "authors": formatted_authors,
            "ISBN": ISBN,
            "publisher": publisher,
            "publishedDate": publishedDate,
            "genre": genre,
            "id": id
        }
        rating = {
            "values": [],
            "average": 0,
            "title": title,
            "id": id
        }
        books_collection.insert_one(book)
        ratings_collection.insert_one(rating)
        return jsonify({'ID': id}), 201
    else:
        return jsonify("Error: Unsupported media type. JSON expected."), 415
    
@app.post('/ratings/<id>/values')
def post_rating(id):
    if request.is_json:
        data = request.json
        try:
            validate(instance=data, schema=rating_post_schema)
        except:
            return jsonify("Error: Missing, wrong type, incorrectly-spelled or extra fields."), 422
        
        value = data.get('value')
        if value not in range(1, 6):
            return jsonify("Error: Only integer values in the range 1-5 are accepted."), 422
        rating = ratings_collection.find_one({'id': id})
        if rating:
            rating['values'].append(value)
            avg = sum(rating['values'])/len(rating['values'])
            rating['average'] = avg
            rating = ratings_collection.find_one_and_update(
            {'id': id}, 
            {'$push': {'values': value}, '$set': {'average': avg}})
            return jsonify(f"Success: Book with id: {id} successfully rated {value}. New average rating: {avg}."), 201
        return jsonify("Error: Book not found"), 404
    else:
        return jsonify("Error: Unsupported media type. JSON expected."), 415

def add_rating_to_top(top, rating):
    id = rating['id']
    title = rating['title']
    average = rating['average']
    formatted_rating = {
        "id": id,
        "title": title,
        "average": average
    }
    top.append(formatted_rating)

@app.get('/top')
def get_top():
    top = []
    # we filter out the ratings with less than 3 values
    filtered_ratings = ratings_collection.find({}, {"_id": 0})
    filtered_ratings = [rating for rating in filtered_ratings if len(rating['values']) >= 3]
    # we sort the ratings by average descending
    filtered_ratings.sort(key=lambda k: k['average'], reverse=True)
    # a counter to count how many max values we have added
    count = 0
    # the current max value
    max = -1
    for rating in filtered_ratings:
        if count > 3:
            break
        if rating['average'] != max:
            max = rating['average']
            count += 1
            add_rating_to_top(top, rating)
        else:
            add_rating_to_top(top, rating)
        
    return jsonify(top), 200
3
if __name__ == '__main__':
    app.run(host = "0.0.0.0", port = 5001, debug=True) 