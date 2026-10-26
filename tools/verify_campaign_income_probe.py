"""Compare direct binary native income oracle buffers exactly on CPU/MPS.

This isolated component probe does not advance a game or measure self-play.
Run large repetitions only under the aggregate CPU/memory guard.
"""
import argparse
from pathlib import Path
from types import SimpleNamespace
import json
import time
import numpy as np
import torch
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studies.campaign.backends.income_kernel import IncomeTensorContext


def verify(directory,device,repeats):
    metadata=json.loads((directory/"metadata.json").read_text())
    B,T,N=len(metadata["cases"]),len(metadata["territories"]),len(metadata["nations"])
    def array(name,shape):return np.fromfile(directory/(name+".i64"),dtype=np.int64).reshape(shape)
    static_t=array("territory_static",(T,3));static_n=array("nation_static",(N,2))
    context=SimpleNamespace(definition_fingerprint=metadata["definition_fingerprint"],territory_ids=metadata["territories"],
        nation_ids=metadata["nations"],int_minimum=metadata["int_min"],int_maximum=metadata["int_max"],
        territory_array=lambda:static_t,nation_array=lambda:static_n)
    before=time.perf_counter();kernel=IncomeTensorContext(context,device=device)
    territories=torch.tensor(array("territory_state",(B,T,4)),dtype=torch.int64,device=device)
    nations=torch.tensor(array("nation_state",(B,N,6)),dtype=torch.int64,device=device)
    sync=lambda:torch.mps.synchronize() if device=="mps" else None
    sync();upload_seconds=time.perf_counter()-before
    result=kernel.compute(territories,nations);sync()
    actual=result.income.cpu().numpy();effective=result.effective.cpu().numpy();effective_errors=result.effective_error.cpu().numpy()
    expected=array("income_oracle",(B,N,6));expected_effective=array("effective_oracle",(B,T,2))
    # Kernel has precise failure categories; oracle reports native exception
    # classes. Undefined C++ signed-overflow fixtures are not in this oracle.
    exception_class=np.array([0,1,1,2,3,1],dtype=np.int64)
    np.testing.assert_array_equal(exception_class[actual[:,:,0]],expected[:,:,0])
    ok=expected[:,:,0]==0;np.testing.assert_array_equal(actual[:,:,1:][ok],expected[:,:,1:][ok])
    np.testing.assert_array_equal(exception_class[effective_errors],expected_effective[:,:,0])
    ok_effective=expected_effective[:,:,0]==0
    np.testing.assert_array_equal(effective[ok_effective],expected_effective[:,:,1][ok_effective])
    before=time.perf_counter()
    for _ in range(repeats):kernel.compute(territories,nations)
    sync();compute_seconds=time.perf_counter()-before
    return {"status":"exact","device":device,"state_cases":B,"nation_slots":N,"territory_slots":T,
        "upload_and_static_setup_seconds":upload_seconds,"repeats":repeats,"synchronized_compute_seconds":compute_seconds,
        "subprobes": [verify(directory / child, device, repeats) for child in metadata.get("subprobes", [])],
        "scope":"Exact income-only kernel on native binary buffers; no phase advance, full game, neural network or training claim"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("directory",type=Path)
    parser.add_argument("--device",choices=("cpu","mps"),default="cpu");parser.add_argument("--repeats",type=int,default=1)
    args=parser.parse_args()
    if args.repeats<=0:parser.error("Positive repetitions required")
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    print(json.dumps(verify(args.directory,args.device,args.repeats),sort_keys=True))
