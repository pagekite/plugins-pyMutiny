dist: mutiny/app.py mutiny/io.py mutiny/irc.py ../HttpdLite/HttpdLite.py
	breeder --compress --header header.txt \
                ../../PySocksipyChain/sockschain \
                ../HttpdLite/HttpdLite.py \
                mutiny/__init__.py mutiny/io.py mutiny/irc.py mutiny/app.py \
                >bin/Mutiny.py
	chmod +x bin/Mutiny.py
	mv bin/Mutiny.py bin/Mutiny-`./bin/Mutiny.py --version`.py

clean:
	rm -f bin/*.py *.pyc */*.pyc
