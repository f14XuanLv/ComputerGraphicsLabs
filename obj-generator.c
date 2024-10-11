#include <stdio.h>
#include <stdlib.h>
#include <math.h>

typedef struct Entry {
    const char *name;
    float (*func)(float, float);
    float x_max;
    float y_max;
    float x_min;
    float y_min;
    float resol;
} Entry;

typedef struct Vertex {
    float x;
    float y;
    float z;
} Vertex;

typedef struct Face {
    int u;
    int v;
    int w;
} Face;

float square(float x, float y) {
    return 1;
}

float cone(float x, float y) {
    return sqrt(pow(x, 2) + pow(y, 2));
}

float sphere(float x, float y) {
    int r = 10;
    return sqrt(pow(r, 2) - pow(x, 2) - pow(y, 2));
}

float ellipsoid(float x, float y) {
    int a = 6;
    int b = 8;
    int c = 10;
    return sqrt((1 - pow(x, 2) / pow(a, 2) - pow(y, 2) / pow(b, 2)) * pow(c, 2));
}

float paraboloid(float x, float y) {
    int a = 4;
    int b = 3;
    return pow(x, 2) / pow(a, 2) + pow(y, 2) / pow(b, 2);
}

float hyperbolic_paraboloid(float x, float y) {
    int a = 4;
    int b = 3;
    return pow(x, 2) / pow(a, 2) - pow(y, 2) / pow(b, 2);
}

int gen_vertices(const Entry *entry, Vertex *buf[], size_t *len) {
    size_t curr = 0;
    size_t vertices = (size_t)(
            ((entry->x_max - entry->x_min) / entry->resol) *
            ((entry->y_max - entry->y_min) / entry->resol)
            );
    if (*buf == NULL) {
        *buf = malloc(vertices * sizeof(Vertex));
        *len = vertices;
    } else if (*len < vertices) {
        return 1;
    }
    for (float y = entry->y_min; y < entry->y_max; y += entry->resol) {
        for (float x = entry->x_min; x < entry->x_max; x += entry->resol) {
            Vertex vertex = {
                .x = x,
                .y = y,
            };
            vertex.z = entry->func(x, y);
            (*buf)[curr++] = vertex;
        }
    }
    return 0;
}

int gen_faces(const Entry *entry, Vertex *vertices, size_t nvertices, Face *buf[], size_t *len) {
    size_t xs = (size_t)((entry->x_max - entry->x_min) / entry->resol);
    size_t ys = (size_t)((entry->y_max - entry->y_min) / entry->resol);
    size_t curr = 0;
    size_t faces = (xs - 1) * (ys - 1) * 2;
    if (*buf == NULL) {
        *buf = malloc(faces * sizeof(Vertex));
        *len = faces;
    } else if (*len < nvertices) {
        return 1;
    }
    for (int y = 0; y < ys - 1; y++) {
        for (int x = 0; x < xs - 1; x++) {
            Face face = {
                .u = y * xs + x + 1,
                .v = y * xs + x + 1 + 1,
                .w = (y + 1) * xs + x + 1
            };
            (*buf)[curr++] = face;
            face.u = face.v;
            face.v = (y + 1) * xs + x + 1 + 1;
            (*buf)[curr++] = face;
        }
    }
    return 0;
}

int main(void) {
    Entry entries[] = {
        {
            .name = "square",
            .func = square,
            .x_max = 10.0f,
            .y_max = 10.0f,
            .x_min = -10.0f,
            .y_min = -10.0f,
            .resol = 1.0f
        },
        {
            .name = "cone",
            .func = cone,
            .x_max = 10.0f,
            .y_max = 10.0f,
            .x_min = -10.0f,
            .y_min = -10.0f,
            .resol = 1.0f
        },
        {
            .name = "sphere",
            .func = sphere,
            .x_max = 10.0f,
            .y_max = 10.0f,
            .x_min = -10.0f,
            .y_min = -10.0f,
            .resol = 1.0f
        },
        {
            .name = "ellipsoid",
            .func = ellipsoid,
            .x_max = 10.0f,
            .y_max = 10.0f,
            .x_min = -10.0f,
            .y_min = -10.0f,
            .resol = 1.0f
        },
        {
            .name = "paraboloid",
            .func = paraboloid,
            .x_max = 10.0f,
            .y_max = 10.0f,
            .x_min = -10.0f,
            .y_min = -10.0f,
            .resol = 1.0f
        },
        {
            .name = "hyperbolic_paraboloid",
            .func = hyperbolic_paraboloid,
            .x_max = 10.0f,
            .y_max = 10.0f,
            .x_min = -10.0f,
            .y_min = -10.0f,
            .resol = 1.0f
        },
    };

    for (int i = 0; i < sizeof(entries) / sizeof(Entry); i++) {
        Vertex *vertices = NULL;
        size_t nvertices = 0;
        if (gen_vertices(&(entries[i]), &vertices, &nvertices) != 0) {
            fprintf(stderr, "Error generating vertices for %s\n", entries[i].name);
            exit(1);
        }
        Face *faces = NULL;
        size_t nfaces = 0;
        if (gen_faces(&(entries[i]), vertices, nvertices, &faces, &nfaces) != 0) {
            fprintf(stderr, "Error generating faces for %s\n", entries[i].name);
            exit(1);
        }
        char buf[FILENAME_MAX];
        snprintf(buf, FILENAME_MAX, "%s.obj", entries[i].name);
        FILE *fp = fopen(buf, "w");
        for (int i = 0; i < nvertices; i++)
            fprintf(fp, "v %f %f %f\n", vertices[i].x, vertices[i].y, vertices[i].z);
        for (int i = 0; i < nfaces; i++)
            fprintf(fp, "f %d %d %d\n", faces[i].u, faces[i].v, faces[i].w);
        fclose(fp);
        free(vertices);
        free(faces);
    }

    return 0;
}
