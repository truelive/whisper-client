build:
    . ./venv/bin/activate && pip install -r requirements.txt

run:
    . ./venv/bin/activate && python main.py

test:
    . ./venv/bin/activate && pytest