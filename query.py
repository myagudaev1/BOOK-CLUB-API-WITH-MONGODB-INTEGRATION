import requests

BASE_URL = "http://localhost:5001" 

books = [
    {
        "title": "Adventures of Huckleberry Finn",
        "ISBN": "9780520343641",
        "genre": "Fiction"
    },
    {
        "title": "The Best of Isaac Asimov",
        "ISBN": "9780385050784",
        "genre": "Science Fiction"
    },
    {
        "title": "Fear No Evil",
        "ISBN": "9780394558783",
        "genre": "Biography"
    },
    {
        "title": "No such book",
        "ISBN": "0000001111111",
        "genre": "Biography"
    },
    {
        "title": "The Greatest Joke Book Ever",
        "authors": "Mel Greene",
        "ISBN": "9780380798490",
        "genre": "Jokes"
    },
    {   
        "title":"The Adventures of Tom Sawyer",
        "ISBN":"9780195810400",
        "genre":"Fiction"
    },
    {   
        "title": "I, Robot",
        "ISBN":"9780553294385",
        "genre":"Science Fiction"
    },
    {   
        "title": "Second Foundation",
        "ISBN":"9780553293364",
        "genre":"Science Fiction"
    }
]

def main():
    selected_books = books[:3] + books[5:8]
    for book in selected_books:
        response = requests.post(f"{BASE_URL}/books", json=book)
        if response.status_code != 201:
            title = book['title']
            ISBN = book['ISBN']
            print(f'Error code {response.status_code} posting book with title: \'{title}\' and ISBN: \'{ISBN}\'.')

    with open('query.txt', 'r') as query_file:
        for query in query_file.readlines():
            query = query.strip()
            print(f'query: {query}')
            response = requests.get(f"{BASE_URL}/books{query}")
            if response.status_code == 200:
                print(f'response: {response.json()}')
            else:
                print(f'response: error {response.status_code}')


if __name__ == '__main__':
    main()
