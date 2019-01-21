import numpy as np
from ffthompy import Timer
from ffthompy.sparse.objects import SparseTensor

def cheby2TERM(Afun, B, x0=None, rank=None, tol=None, par=None, callback=None):
    """
    Chebyshev two-term iterative solver

    Parameters
    ----------
    Afun : a function, represnting linear function A in the system Ax =B
    B : sparse tensor representing vector B in the right-hand side of linear system
    x0 : sparse tensor representing initial approximation of solution of linear system
    par : dict
          parameters of the method
    callback :

    Returns
    -------
    x : resulting unknown vector
    res : dict
        results
    """
    if par is None:
        par = dict()
    if 'tol' not in par:
        par['tol'] = 1e-06
    if 'maxiter' not in par:
        par['maxiter'] = 1e7
    if 'eigrange' not in par:
        raise NotImplementedError("It is necessary to calculate eigenvalues.")
    else:
        Egv = par['eigrange']

    res={'norm_res': [],
           'kit': 0}

    bnrm2 = B.norm()
    Ib = 1.0/bnrm2
    if bnrm2 == 0:
        bnrm2 = 1.0

    if x0 is None:
        x=B
    else:
        x=x0

    r = B - Afun(x)
    r0=r.norm()
    res['norm_res'].append(Ib*r0)# For Normal Residue

    if res['norm_res'][res['kit']] < par['tol']: # if errnorm is less than tol
        return x, res

    M=SparseTensor(kind=x.kind, val=np.ones(x.N.size*[3,]), rank=1) # constant field
    FM=M.fourier().enlarge(x.N)

    d = (Egv[1]+Egv[0])/2.0 # np.mean(par['eigrange'])
    c = (Egv[1]-Egv[0])/2.0 # par['eigrange'][1] - d
    v = x*0.0
    while (res['norm_res'][res['kit']] > par['tol']) and (res['kit'] < par['maxiter']):
        res['kit'] += 1
        x_prev = x
        if res['kit'] == 1:
            p = 0
            w = 1/d
        elif res['kit'] == 2:
            p = -(1/2)*(c/d)*(c/d)
            w = 1/(d-c*c/2/d)
        else:
            p = -(c*c/4)*w*w
            w = 1/(d-c*c*w/4)
        v = (r - p*v).truncate(rank=rank, tol=tol)
        x = (x_prev + w*v)
        x=(-FM*x.mean()+x).truncate(rank=rank, tol=tol) # setting correct mean
        r = B - Afun(x)

        res['norm_res'].append((1.0/r0)*r.norm())
#        print(res['kit'])
#        print("w is:",w)
#        print(res['norm_res'][res['kit']])
#        print

        if callback is not None:
            callback(x)

    if par['tol'] < res['norm_res']: # if tolerance is less than error norm
        print("Chebyshev solver does not converges!")
    else:
        print("Chebyshev solver converges.")

    if res['kit'] == 0:
        res['norm_res'] = 0
    return x, res

def minimal_residual(Afun, B, x0=None, rank=None, tol=None, par=None, norm=None):

    res={'norm_res': [],
           'kit': 0}
    if x0 is None:
        x=B
    else:
        x=x0
    if norm is None:
        norm=lambda X: X.norm(normal_domain=False)

    residuum= B-Afun(x)
    res['norm_res'].append(norm(residuum))
    beta=Afun(residuum)

    M=SparseTensor(kind=x.kind, val=np.ones(x.N.size*[3,]), rank=1) # constant field
    FM=M.fourier().enlarge(x.N)

    norm_res= res['norm_res'][res['kit']]

    while (norm_res>par['tol'] and res['kit']<par['maxiter']):
        res['kit']+=1

        if par['approx_omega']:
            omega=norm_res/norm(beta) # approximate omega
        else:
            omega= beta.inner(residuum)/norm(beta)**2 #exact formula

            if abs(omega)<1e-1:
            #beta and residuum could be orthogonal, in this case omega is very small
            #and x is trapped, the convergence stopped.
            #to escape from this pitfall, use another approximate of omega.
                omega=norm_res/norm(beta)

        x=(x+residuum*omega)
        x=(-FM*x.mean()+x).truncate(rank=rank, tol=tol) # setting correct mean

        if res['kit']%10==0: #every 10 iteration compute once the true residuum
            residuum= B-Afun(x)
        else:
            residuum = (residuum - beta*omega).truncate(rank=rank, tol=tol)

        norm_res = norm(residuum)
        if par['divcrit'] and norm_res>res['norm_res'][res['kit']-1]:
            break
        res['norm_res'].append(norm_res)

#        print(res['kit'])
#        print("omega is  :",omega)
#        print(res['norm_res'][res['kit']])
#        print

        beta=Afun(residuum)

    return x, res

def richardson(Afun, B, x0=None, rank=None, tol=None, par=None, norm=None):
    if isinstance(par['alpha'], float):
        omega=1./par['alpha']
    else:
        raise ValueError()
    res={'norm_res': [],
           'kit': 0}
    if x0 is None:
        x=B*omega
    else:
        x=x0

    if norm is None:
        norm=lambda X: X.norm()

    res['norm_res'].append(norm(B))

    M=SparseTensor(kind=x.kind, val=np.ones(x.N.size*[3,]), rank=1) # constant field
    FM=M.fourier().enlarge(x.N)

    norm_res=1e15
    while (norm_res>par['tol'] and res['kit']<par['maxiter']):
        res['kit']+=1
        residuum= B-Afun(x)
        norm_res = norm(residuum)
        if par['divcrit'] and norm_res>res['norm_res'][res['kit']-1]:
            break

        x=(x+residuum*omega)
        x=(-FM*x.mean()+x).truncate(rank=rank, tol=tol) # setting correct mean

        res['norm_res'].append(norm_res)

    return x, res

def richardson_debug(Afun, B, x0=None, rank=None, tol=None, par=None, norm=None):
    if isinstance(par['alpha'], float):
        omega=1./par['alpha']
    else:
        raise ValueError()
    res={'norm_res': [],
           'kit': 0}
    if x0 is None:
        x=B*omega
    else:
        x=x0
    x=x.truncate(rank=rank, tol=tol)


    if norm is None:
        norm=lambda X: X.norm()

    norm_res=1e15
    while (norm_res>par['tol'] and res['kit']<par['maxiter']):
        res['kit']+=1
        tic=Timer(name='Afun(x)')
        Afunx=Afun(x)
        tic.measure()
        tic=Timer(name='residuum')
        residuum=B-Afunx
        tic.measure()
        tic=Timer(name='iteration')
        x=(x+residuum*omega).truncate(rank=rank, tol=tol)
        tic.measure()
        tic=Timer(name='norm_residuum')
        norm_res=norm(residuum)
        tic.measure()
        res['norm_res'].append(norm_res)

    res['norm_res'].append(norm(B-Afun(x)))
    return x, res
