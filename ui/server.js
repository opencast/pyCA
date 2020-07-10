#!/usr/bin/env node

const Bundler = require('parcel-bundler');
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');


const app = express();

app.use(createProxyMiddleware('/api', {
  target: 'http://127.0.0.1:5000'
}));

app.use(createProxyMiddleware('/img', {
  target: 'http://127.0.0.1:5000'
}));

const bundler = new Bundler('ui/index.html');
app.use(bundler.middleware());

const port = Number(process.env.PORT || 1234);
app.listen(port, () => console.log(`Listening on http://127.0.0.1:${port}`));
