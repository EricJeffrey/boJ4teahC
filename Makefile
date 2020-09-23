
.PHONY: server

server: server/*.cpp server/*.h
	g++ -Wall -lpthread -o server/boJ4teahCd server/*.cpp