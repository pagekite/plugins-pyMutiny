bin/Mutiny.combined.py: Mutiny.py ../HttpdLite/HttpdLite.py
	breeder ../HttpdLite/HttpdLite.py Mutiny.py >bin/Mutiny.combined.py
	chmod +x bin/Mutiny.combined.py

clean:
	rm -f bin/*.combined.py *.pyc
