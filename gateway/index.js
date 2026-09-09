const express = require("express");
const app = express();
const port = 3001;

const apiRoutes = require("./routes/api.routes");

app.use(express.json());


const cors = require('cors');
app.use(cors());  // permet au backend et au frontEnd de communiquer meme s'il se sont sur deux origines différentes



app.use("/api", apiRoutes);

app.listen(port, () => {
  console.log(`Gateway démarrée sur http://localhost:${port}`);
});
