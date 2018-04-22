THIRD_PARTY_DEPS=bootstrap.min.css \
								 bootstrap.min.js \
								 bootstrap-theme.min.css \
								 jquery-1.12.0.min.js \
								 jquery.jsonrpcclient.js\
								 jquery.color-2.1.2.min.js\
								 require.js\
								 jquery-ui-1.11.4
#								 help-icon.png
#								 doge.jpg\
								 crafty-min.js

all: $(THIRD_PARTY_DEPS) ts-files

typings:
	npm install

ts-files: typings
	tsc

bootstrap.min.css:
	wget https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css

bootstrap.min.js:
	wget https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js

bootstrap-theme.min.css:
	wget https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css

jquery-1.12.0.min.js:
	wget https://code.jquery.com/jquery-1.12.0.min.js

jquery.jsonrpcclient.js:
	wget https://raw.githubusercontent.com/Textalk/jquery.jsonrpcclient.js/master/jquery.jsonrpcclient.js

jquery.color-2.1.2.min.js:
	wget https://code.jquery.com/color/jquery.color-2.1.2.min.js

require.js:
	wget http://requirejs.org/docs/release/2.3.5/minified/require.js

#crafty-min.js:
#	wget https://github.com/craftyjs/Crafty/releases/download/0.7.0/crafty-min.js

jquery-ui-1.11.4:
	wget https://jqueryui.com/resources/download/jquery-ui-1.11.4.zip
	unzip jquery-ui-1.11.4.zip
	rm jquery-ui-1.11.4.zip

#doge.jpg:
#	wget -O doge.jpg https://pbs.twimg.com/profile_images/378800000822867536/3f5a00acf72df93528b6bb7cd0a4fd0c.jpeg

help-icon.png:
	wget https://cseweb.ucsd.edu/~r1jha/images/help-icon.png

clean:
	rm -r $(THIRD_PARTY_DEPS)
