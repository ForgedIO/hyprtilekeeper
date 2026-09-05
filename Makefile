CXX ?= c++
CXXFLAGS := -std=c++23 -O2 -fPIC -Wall -Wextra -Wpedantic $(shell pkg-config --cflags hyprland)
LDFLAGS := -shared

.PHONY: all clean

all: hyprtilekeeper.so

hyprtilekeeper.so: src/main.cpp
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@.tmp $<
	mv $@.tmp $@

clean:
	$(RM) hyprtilekeeper.so
