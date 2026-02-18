// ===== LOAD MODEL =====
var modelPath = "/github/workspace/model/archiPKG.archimate";
var model = archi.loadModel(modelPath);
if (!model) {
    console.log("MODEL TIDAK DITEMUKAN: " + modelPath);
    exit();
}

// ===== BUAT FOLDER OUTPUT =====
var outputFolder = "/github/workspace/model/diagrams";
var folder = new java.io.File(outputFolder);


if (!folder.exists()) folder.mkdirs();

// ===== AMBIL SEMUA VIEW =====
var views = model.getAllViews();

// ===== EXPORT PNG =====
for (var i = 0; i < views.size(); i++) {
    var view = views.get(i);
    var safeName = view.getName().replace(/[^a-zA-Z0-9]/g, "_");
    var outputPath = outputFolder + "/" + safeName + ".png";
    archi.commandLine.exportView(model, view, outputPath, "png");
    console.log("Exported: " + outputPath);
}

// ===== CLOSE =====
model.close();
console.log("SELESAI EXPORT SEMUA DIAGRAM");
