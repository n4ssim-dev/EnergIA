const express = require("express");
const app = express();
const port = 3001;

const apiRoutes = require("./routes/api.routes");

app.use(express.json());

app.use("/api", apiRoutes);

app.listen(port, () => {
  console.log(`Gateway démarrée sur http://localhost:${port}`);
});
