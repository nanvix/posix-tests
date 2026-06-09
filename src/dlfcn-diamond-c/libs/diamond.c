/*
 * Copyright(c) The Maintainers of Nanvix.
 * Licensed under the MIT License.
 *
 * libdiamond.so - root of the diamond. Pulls in libleft.so and
 * libright.so via DT_NEEDED. Both arms transitively depend on
 * libbase.so, so a correct loader must consolidate the two
 * "DT_NEEDED libbase.so" edges onto a single libbase.so instance.
 */

extern int left_bump(void);
extern int right_bump(void);
extern int right_get(void);

int diamond_left(void)
{
    return left_bump();
}

int diamond_right(void)
{
    return right_bump();
}

int diamond_observe(void)
{
    return right_get();
}
