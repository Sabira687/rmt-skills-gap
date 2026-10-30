// OCR of selected PDF pages with the macOS Vision framework (no extra installation).
// usage: swift code/ocr_pdf.swift <pdf> <first_page> <last_page> <rotation: 0|90|180|270> <out.txt>
import Foundation
import PDFKit
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count == 6, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])),
      let first = Int(args[2]), let last = Int(args[3]), let rot = Int(args[4]) else {
    print("usage: ocr_pdf.swift <pdf> <first> <last> <rotation> <out.txt>"); exit(1)
}
var out = ""
for n in first...min(last, doc.pageCount) {
    guard let page = doc.page(at: n - 1) else { continue }
    page.rotation = (page.rotation + rot) % 360
    let b = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2.6
    let size = CGSize(width: b.width * scale, height: b.height * scale)
    let img = page.thumbnail(of: size, for: .mediaBox)
    guard let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["en-US"]
    req.usesLanguageCorrection = true
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    out += "\n=====PAGE \(n)=====\n"
    for obs in req.results ?? [] {
        if let t = obs.topCandidates(1).first { out += t.string + "\n" }
    }
}
try? out.write(toFile: args[5], atomically: true, encoding: .utf8)
print("pages \(first)-\(last) -> \(args[5]), \(out.count) chars")
