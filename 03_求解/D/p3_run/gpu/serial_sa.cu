typedef unsigned long long U64;

__device__ U64 mix_seed(U64 z) {
    z += 0x9e3779b97f4a7c15ULL;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

__device__ U64 draw(U64 &state) {
    state ^= state >> 12;
    state ^= state << 25;
    state ^= state >> 27;
    return state * 0x2545f4914f6cdd1dULL;
}

__device__ int site(U64 &state, int n) {
    U64 count = (U64)n;
    U64 min_value = (-count) % count;
    U64 r;
    do { r = draw(state); } while (r < min_value);
    return r % count;
}

__device__ int delta_e(int spin, int field) {
    return 4 * spin * field;
}

__device__ bool accept(int delta, double temp, double u) {
    return delta <= 0 || u < exp(-double(delta) / temp);
}

// Sites are stored spin-major. Each thread owns a whole physical Ising restart.
extern "C" __global__ void prepare(int m, int n, const U64 *seeds, const int *ptr,
  const int *cols, const int *w, U64 *rng, int *h, signed char *s, signed char *best,
  int *energy, int *best_e) {
    int a = blockIdx.x * blockDim.x + threadIdx.x;
    if (a >= m) return;
    U64 r = mix_seed(seeds[a]);
    if (!r) r = 1;
    for (int j=0; j<n; ++j)
        best[j*m+a] = s[j*m+a] = (draw(r) >> 63) ? 1 : -1;
    int e = 0;
    for (int j=0; j<n; ++j) {
        int f = 0;
        for (int k=ptr[j]; k<ptr[j+1]; ++k) f += w[k] * s[cols[k]*m+a];
        h[j*m+a] = f;
        e -= f * s[j*m+a];
    }
    energy[a] = best_e[a] = e;
    rng[a] = r;
}

// Splitting temperature steps across CUDA launches is solely for WDDM time slicing.
// All spin, field, RNG, energy and best-vector state persists between launches.
extern "C" __global__ void cool(int m, int n, int start_t, int end_t, const double *temps,
  const int *ptr, const int *cols, const int *w, U64 *rng, int *h, signed char *s,
  signed char *best, int *energy, int *best_e) {
    int a = blockIdx.x * blockDim.x + threadIdx.x;
    if (a >= m) return;
    U64 r = rng[a];
    int e = energy[a], b = best_e[a];
    for (int t=start_t; t<end_t; ++t) {
        for (int step=0; step<n; ++step) {
            int j = site(r,n);
            int spin = s[j*m+a];
            int d = delta_e(spin,h[j*m+a]);
            double u = double(draw(r) >> 11) / 9007199254740992.0;
            if (!accept(d, temps[t], u)) continue;
            s[j*m+a] = -spin;
            for (int k=ptr[j]; k<ptr[j+1]; ++k)
                h[cols[k]*m+a] -= 2*spin*w[k];
            e += d;
            if (e < b) {
                b = e;
                for (int l=0; l<n; ++l) best[l*m+a] = s[l*m+a];
            }
        }
    }
    energy[a] = e;
    best_e[a] = b;
    rng[a] = r;
}

extern "C" __global__ void verify_move(int m, int n, const int *w, const int *state_id,
  const int *sites, const double *temps, const double *uniforms,
  int *out_e, int *out_d, int *out_id) {
    int a = blockIdx.x * blockDim.x + threadIdx.x;
    if (a >= m) return;
    int seq=state_id[a], site=sites[a], e=0, selh=0;
    for (int i=0; i<n; ++i) {
        int field=0;
        for (int j=0;j<n;++j) field+=w[i*n+j]*((seq & (1<<j)) ? 1 : -1);
        int spin=(seq & (1<<i)) ? 1 : -1;
        e -= spin*field;
        if (i==site) selh=field;
    }
    int spin=(seq & (1<<site)) ? 1 : -1;
    int d=delta_e(spin,selh);
    out_e[a]=e;
    out_d[a]=d;
    out_id[a]=accept(d,temps[a],uniforms[a]) ? (seq ^ (1<<site)) : seq;
}
