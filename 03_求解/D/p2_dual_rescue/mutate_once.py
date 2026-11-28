"""One top-level SDK call. First returned matrix is saved before any audit."""
import argparse,random,time
from common import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--id',required=True);ap.add_argument('--anchor',required=True);args=ap.parse_args()
    reg=verify_registration(args.anchor);row=next(r for r in reg['candidates_A'] if r['id']==args.id)
    dest=OUT/'mutate'/args.id;dest.mkdir(parents=True,exist_ok=True)
    write_new(dest/'attempt.json',dict(time=now(),candidate=row,anchor=args.anchor,top_level_call_limit=1))
    start=time.monotonic()
    try:
        initialize_license()
        import kaiwu as kw,requests
        original=requests.sessions.Session.request
        def no_network(*a,**k):raise RuntimeError('Network disabled during local mutate')
        requests.sessions.Session.request=no_network
        random.seed(row['external_seed']);np.random.seed(row['external_seed'])
        J=np.load(ROOT/row['J']).copy()
        write_new(dest/'call_started.json',dict(time=now(),parameters=reg['mutate'],input_sha256=sha(ROOT/row['J'])))
        result=kw.preprocess.perform_precision_adaption_mutate(J,iterations=100,heuristic='greedy',decision='heuristic')
        # Archive the first complete output before assessing shape, precision or quality.
        output=dest/'first_output.npy';save_array(output,np.asarray(result))
        write_new(dest/'first_output_receipt.json',dict(time=now(),file=str(output.relative_to(ROOT)),sha256=sha(output),seconds=time.monotonic()-start,top_level_calls=1))
        requests.sessions.Session.request=original
        print(json.dumps(dict(id=args.id,output_sha256=sha(output),seconds=time.monotonic()-start)),flush=True)
    except Exception as e:
        write_new(dest/'error.json',dict(time=now(),error_type=type(e).__name__,error=str(e)[:600],seconds=time.monotonic()-start))
        raise

if __name__=='__main__':main()
