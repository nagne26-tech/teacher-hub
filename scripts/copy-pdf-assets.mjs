import {cpSync,mkdirSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const root=dirname(require.resolve('pdfjs-dist/package.json'));
mkdirSync('public/pdf-assets',{recursive:true});
for(const folder of ['cmaps','standard_fonts','wasm'])cpSync(resolve(root,folder),`public/pdf-assets/${folder}`,{recursive:true});
