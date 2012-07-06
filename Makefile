bin/Mutiny.combined.py: mutiny/app.py ../HttpdLite/HttpdLite.py
	breeder --header header.txt \
                ../HttpdLite/HttpdLite.py mutiny/app.py \
                >bin/Mutiny.py
	chmod +x bin/Mutiny.py

clean:
	rm -f bin/*.py *.pyc */*.pyc
