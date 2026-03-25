# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

PROGRAM_NAME := echo-cpp

SOURCES := $(wildcard *.cpp)
OBJECTS := $(SOURCES:.cpp=.o)
BINARY  := $(PROGRAM_NAME).elf

all: $(OBJECTS)
	$(CXX) $(LDFLAGS) $(OBJECTS) $(LIBRARIES_CXX) -o $(BINARIES_DIR)/$(BINARY)

clean:
	rm -f $(OBJECTS)
	rm -f $(BINARIES_DIR)/$(BINARY)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) $< -c -o $@
