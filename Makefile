.PHONY = gen-objs

gen-objs: obj-generator
	./obj-generator
	mv *.obj Object/

obj-generator: obj-generator.c
	cc -Wall -Wextra -O2 -lm -o obj-generator obj-generator.c
