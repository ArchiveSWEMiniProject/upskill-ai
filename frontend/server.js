const http = require("http");

const port = process.env.PORT || 3000;

const server = http.createServer((req, res) => {
  res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
  res.end(`<!DOCTYPE html>
<html>
  <head>
    <title>UpSkill-AI</title>
  </head>
  <body style="font-family: sans-serif; padding: 2rem;">
    <h1>UpSkill-AI Web</h1>
    <p>Frontend scaffolding service is running.</p>
  </body>
</html>`);
});

server.listen(port, "0.0.0.0", () => {
  console.log(`upskill-web listening on port ${port}`);
});
