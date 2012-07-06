dist: mutiny/app.py mutiny/io.py mutiny/irc.py ../HttpdLite/HttpdLite.py
	breeder --compress --header header.txt \
                ../../PySocksipyChain/sockschain \
                ../HttpdLite/HttpdLite.py \
                mutiny/__init__.py mutiny/io.py mutiny/irc.py mutiny/app.py \
                >bin/mutiny-tmp.py
	chmod +x bin/mutiny-tmp.py
	mv bin/mutiny-tmp.py bin/mutiny-`./bin/mutiny-tmp.py --version`.py

clean:
	rm -f bin/mutiny-*.py *.pyc */*.pyc
