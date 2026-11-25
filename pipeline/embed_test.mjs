import { pipeline, env } from '@xenova/transformers';
env.localModelPath = '/home/user/nobel-index/pipeline/models/'; env.allowRemoteModels = false;
const ext = await pipeline('feature-extraction', 'Xenova/bge-small-en-v1.5', { quantized: true });
const o = await ext(['mRNA vaccines nucleoside modification', 'nucleoside base modifications that enabled effective mRNA vaccines', 'auction theory'], { pooling: 'cls', normalize: true });
const v = o.tolist(); const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
console.log(dot(v[0],v[1]), dot(v[0],v[2]));
