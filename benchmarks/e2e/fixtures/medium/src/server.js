import http from 'node:http';

import { handler } from './app.js';

const port = Number(process.env.PORT ?? 3000);
http.createServer(handler).listen(port, () => console.log(`tasks-api on :${port}`));
