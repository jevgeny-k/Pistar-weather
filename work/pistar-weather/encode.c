#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "md380_vocoder.h"

/* One process per announcement: the firmware encoder keeps internal state. */
int main(int argc, char **argv) {
    int decode = argc == 4 && strcmp(argv[1], "-d") == 0;
    if (argc != 3 && !decode) { fprintf(stderr, "usage: encode [-d] input output\n"); return 2; }
    FILE *in = fopen(argv[decode?2:1], "rb"), *out = fopen(argv[decode?3:2], "wb");
    if (!in || !out) { perror("fopen"); return 1; }
    if (md380_init() != 0) { perror("md380_init"); return 1; }
    int16_t pcm[160]; uint8_t ambe[9]; size_t n, frames = 0;
    if (decode) {
        while (fread(ambe, 1, 9, in) == 9) {
            md380_decode_fec(ambe, pcm);
            if (fwrite(pcm, sizeof(int16_t), 160, out) != 160) return 1;
        }
        fclose(in); return fclose(out) ? 1 : 0;
    }
    while ((n = fread(pcm, sizeof(int16_t), 160, in))) {
        if (n < 160) memset(pcm + n, 0, (160-n)*sizeof(int16_t));
        memset(ambe, 0, sizeof(ambe)); md380_encode_fec(ambe, pcm);
        if (fwrite(ambe, 1, 9, out) != 9) return 1;
        frames++;
    }
    fclose(in); if (fclose(out)) return 1;
    fprintf(stderr, "Encoded %zu AMBE72 frames\n", frames);
    return 0;
}
