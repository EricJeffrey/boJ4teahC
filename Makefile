
.PHONY: server

server: server/*.cpp server/*.h
	g++ -Wall -o server/boJ4teahCd server/*.cpp -lpthread