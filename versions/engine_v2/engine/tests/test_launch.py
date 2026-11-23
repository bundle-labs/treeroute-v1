"""G-THREADS launcher: pins before numpy, threadpoolctl verified, sklearnex required. Each test
runs in a fresh interpreter because thread pins are process-wide."""

import json

from conftest import run_python


def _result(proc):
    assert proc.returncode == 0, proc.stdout + proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")][-1]
    return json.loads(line[len("RESULT "):])


def test_pins_are_applied_and_recorded():
    res = _result(run_python("""
        import os, sys, json
        os.environ['OPENBLAS_NUM_THREADS'] = '13'   # a shell value the launcher must overwrite
        from treeroute import launch
        rec = launch.pin_threads()
        import threadpoolctl
        pools = [(d['user_api'], d['num_threads']) for d in threadpoolctl.threadpool_info()]
        import daal4py
        print('RESULT ' + json.dumps({
            'env': {k: os.environ.get(k) for k in launch.PIN_ENV_VARS},
            'before': rec['env_before_pins']['OPENBLAS_NUM_THREADS'],
            'pools': pools, 'onedal': daal4py.num_threads(),
            'workers': rec['workers'], 'sklearnex': rec['backend']['sklearnex_version']}))
    """))
    assert set(res["env"].values()) == {"4"}
    assert res["before"] == "13"
    assert res["pools"] and all(n == 4 for _, n in res["pools"])
    assert any(api == "blas" for api, _ in res["pools"])
    assert res["onedal"] == 4
    assert res["workers"] == {"forest_threads": 4, "blas_threads": 4, "tree_predict_workers": 8,
                              "router_workers": 8, "router_worker_blas_threads": 1}
    assert res["sklearnex"]


def test_numpy_imported_first_is_refused():
    res = _result(run_python("""
        import json
        import numpy
        from treeroute import launch
        from treeroute.errors import LaunchError
        try:
            launch.pin_threads()
            out = 'no error'
        except LaunchError as e:
            out = str(e)
        print('RESULT ' + json.dumps(out))
    """))
    assert "imported before the thread pins" in res and "numpy" in res


def test_missing_sklearnex_fails_loudly():
    res = _result(run_python("""
        import json, sys

        class Block(object):   # makes 'import sklearnex' raise ImportError, as if not installed
            def find_spec(self, name, path=None, target=None):
                if name == 'sklearnex' or name.startswith('sklearnex.'):
                    raise ImportError('sklearnex blocked by the test')
                return None

        sys.meta_path.insert(0, Block())
        from treeroute import launch
        from treeroute.errors import LaunchError
        try:
            launch.pin_threads()
            out = 'no error'
        except LaunchError as e:
            out = str(e)
        print('RESULT ' + json.dumps(out))
    """))
    assert "sklearnex is required" in res


def _launch_with_env(name, value):
    return _result(run_python("""
        import json, os
        os.environ[%r] = %r
        from treeroute import launch
        from treeroute.errors import LaunchError
        import sys
        try:
            launch.pin_threads()
            out = 'no error'
        except LaunchError as e:
            out = str(e)
        print('RESULT ' + json.dumps({'out': out, 'numpy': 'numpy' in sys.modules}))
    """ % (name, value)))


def test_foreign_numeric_environment_variables_are_refused():
    for name, value in (("MKL_CBWR", "AVX2"), ("OPENBLAS_CORETYPE", "Haswell"),
                        ("OMP_THREAD_LIMIT", "2"), ("KMP_AFFINITY", "compact"),
                        ("PYTHONHASHSEED", "0"), ("SKLEARNEX_VERBOSE", "INFO"),
                        ("TBB_NUM_THREADS", "3"), ("omp_proc_bind", "true")):
        res = _launch_with_env(name, value)
        assert "environment variables that the numeric libraries read" in res["out"], (name, res)
        assert name.upper() in res["out"].upper()
        assert res["numpy"] is False  # refused before anything numeric loaded


def test_foreign_environment_helper_spares_the_pins_and_other_variables():
    from treeroute import launch

    env = {"OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "13", "PATH": "x", "MKL_CBWR": "AVX",
           "GOTO_NUM_THREADS": "2", "HOME": "h", "NPY_PROMOTION_STATE": "weak"}
    assert launch.foreign_environment(env) == {"GOTO_NUM_THREADS": "2", "MKL_CBWR": "AVX",
                                               "NPY_PROMOTION_STATE": "weak"}


def test_tbb_version_enters_the_fingerprint():
    from treeroute.runs.fingerprint import VERSIONED_DISTRIBUTIONS, library_versions

    assert "tbb" in VERSIONED_DISTRIBUTIONS
    assert library_versions()["tbb"]  # installed here (oneDAL's threading layer)


def test_record_refuses_without_launch():
    res = _result(run_python("""
        import json
        from treeroute import launch
        from treeroute.errors import LaunchError
        try:
            launch.record()
            out = 'no error'
        except LaunchError as e:
            out = str(e)
        print('RESULT ' + json.dumps(out))
    """))
    assert "not started through treeroute.launch" in res
