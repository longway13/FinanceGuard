"use client"

import { useState, useRef } from "react"
import {
  PdfLoader,
  PdfHighlighter,
  Highlight,
  TextHighlight,
  AreaHighlight,
  useHighlightContainerContext,
  usePdfHighlighterContext,
  MonitoredHighlightContainer,
  Tip,
  PdfHighlighterUtils,
  ViewportHighlight,
} from "react-pdf-highlighter-extended"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { Trash2, Camera, Loader2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface PdfViewerProps {
  fileId: string
  onTextSelect?: (text: string) => void
  isLoading?: boolean
  url?: string
}

// Custom highlight interface with additional properties
interface CustomHighlight extends Omit<Highlight, 'position'> {
  comment?: string
  category?: "default" | "important" | "question"
  imageUrl?: string
  position: {
    boundingRect: {
      x1: number
      y1: number
      x2: number
      y2: number
      width: number
      height: number
      pageNumber: number
    }
    rects: Array<any>
  }
}

interface AreaAnalysisResponse {
  text?: string
  analysis?: string
  error?: string
}

// 백엔드 응답을 위한 인터페이스 추가
interface ToxicClauseResponse {
  text: string;
  position: {
    pageNumber: number;
    boundingRect: {
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      width: number;
      height: number;
    };
  };
}

// Function to send area screenshot to backend
async function sendAreaToBackend(data: {
  image: string
  position: {
    boundingRect: {
      x1: number
      y1: number
      x2: number
      y2: number
    }
    pageNumber: number
  }
}): Promise<AreaAnalysisResponse> {
  try {
    const response = await fetch('/api/analyze-area', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      throw new Error('Failed to analyze area')
    }

    return await response.json()
  } catch (error) {
    console.error('Error analyzing area:', error)
    throw error
  }
}

// Highlight popup component
const HighlightPopup = ({ highlight }: { highlight: ViewportHighlight<CustomHighlight> }) => {
  return (
    <div className="bg-white shadow-lg rounded-lg p-2 border">
      <div className="flex items-center gap-2">
        <span className="text-sm">{highlight.content?.text}</span>
        {highlight.comment && (
          <div className="text-xs text-muted-foreground">{highlight.comment}</div>
        )}
        {highlight.imageUrl && (
          <img 
            src={highlight.imageUrl} 
            alt="Captured area" 
            className="max-w-[200px] h-auto rounded border"
          />
        )}
      </div>
    </div>
  )
}

// Custom highlight container
const HighlightContainer = ({ 
  editHighlight,
  onAreaCapture,
}: { 
  editHighlight: (id: string, edit: Partial<CustomHighlight>) => void
  onAreaCapture: (image: string, position: any) => void
}) => {
  const {
    highlight,
    isScrolledTo,
    screenshot,
    viewportToScaled,
  } = useHighlightContainerContext<CustomHighlight>()

  const [isCapturing, setIsCapturing] = useState(false)
  const { toast } = useToast()

  const isTextHighlight = !Boolean(highlight.content?.image)

  let highlightColor = "rgba(255, 226, 143, 0.3)"
  if (highlight.category === "important") {
    highlightColor = "rgba(239, 90, 104, 0.3)"
  } else if (highlight.category === "question") {
    highlightColor = "rgba(154, 208, 220, 0.3)"
  }

  const handleAreaCapture = async () => {
    try {
      setIsCapturing(true)
      const image = screenshot(highlight.position.boundingRect)
      const scaledPosition = viewportToScaled(highlight.position.boundingRect)
      
      await onAreaCapture(image, {
        boundingRect: scaledPosition,
        pageNumber: highlight.position.pageNumber,
      })

      toast({
        title: "Area captured",
        description: "The selected area has been captured and sent for analysis",
      })
    } catch (error) {
      toast({
        title: "Error capturing area",
        description: "Failed to capture and analyze the selected area",
        variant: "destructive",
      })
    } finally {
      setIsCapturing(false)
    }
  }

  const component = isTextHighlight ? (
    <TextHighlight
      highlight={highlight}
      isScrolledTo={isScrolledTo}
      style={{ background: highlightColor }}
    />
  ) : (
    <AreaHighlight
      highlight={highlight}
      isScrolledTo={isScrolledTo}
      style={{ background: highlightColor }}
    />
  )

  const highlightTip: Tip = {
    position: highlight.position,
    content: (
      <div className="bg-white shadow-lg rounded-lg p-2 border">
        <div className="flex items-center gap-2">
          <HighlightPopup highlight={highlight} />
          <Button
            size="sm"
            variant="outline"
            onClick={handleAreaCapture}
            disabled={isCapturing}
          >
            {isCapturing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Camera className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    ),
  }

  return (
    <MonitoredHighlightContainer
      highlightTip={highlightTip}
      key={highlight.id}
    >
      {component}
    </MonitoredHighlightContainer>
  )
}

// Selection tip component
const SelectionTip = () => {
  const { getCurrentSelection } = usePdfHighlighterContext()

  const createHighlight = (category: CustomHighlight["category"]) => {
    const selection = getCurrentSelection()
    if (selection) {
      const highlight = {
        content: selection.content,
        position: selection.position,
        category,
        id: Math.random().toString(16).slice(2),
      }
      selection.emit("finishSelection", highlight)
    }
  }

  return (
    <div className="bg-white shadow-lg rounded-lg p-2 border">
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => createHighlight("default")}
        >
          Highlight
        </Button>
        <Button
          size="sm"
          variant="destructive"
          onClick={() => createHighlight("important")}
        >
          Important
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => createHighlight("question")}
        >
          Question
        </Button>
      </div>
    </div>
  )
}

// 백엔드 통신 함수 추가
async function analyzeToxicClauses(pdfId: string): Promise<ToxicClauseResponse[]> {
  try {
    const response = await fetch(`/api/analyze-toxic-clauses?pdfId=${pdfId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to analyze toxic clauses');
    }

    return await response.json();
  } catch (error) {
    console.error('Error analyzing toxic clauses:', error);
    throw error;
  }
}

export function PdfViewer({ fileId, onTextSelect, url }: PdfViewerProps) {
  const [highlights, setHighlights] = useState<CustomHighlight[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const highlighterUtilsRef = useRef<PdfHighlighterUtils>(null)
  const { toast } = useToast()

  // 하이라이트 생성 함수
  const createHighlight = (text: string, position: {
    pageNumber: number;
    boundingRect: {
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      width: number;
      height: number;
    };
  }) => {
    const newHighlight: CustomHighlight = {
      id: `highlight-${Date.now()}`,
      position: {
        boundingRect: {
          ...position.boundingRect,
          pageNumber: position.pageNumber
        },
        rects: []
      },
      content: {
        text: text
      },
      comment: `위험 조항: ${text}`,
      category: "important"
    };

    setHighlights(prev => [...prev, newHighlight]);
  };

  // 독소 조항 분석 및 하이라이트 함수
  const analyzeAndHighlightToxicClauses = async () => {
    try {
      const toxicClauses = await analyzeToxicClauses(fileId);
      
      // 기존 하이라이트 초기화
      setHighlights([]);
      
      // 각 독소 조항에 대해 하이라이트 생성
      toxicClauses.forEach(clause => {
        createHighlight(clause.text, clause.position);
      });

      toast({
        title: "분석 완료",
        description: `${toxicClauses.length}개의 위험 조항이 발견되었습니다.`,
      });
    } catch (error) {
      toast({
        title: "분석 실패",
        description: "위험 조항 분석 중 오류가 발생했습니다.",
        variant: "destructive",
      });
    }
  };

  // 테스트를 위한 버튼 추가
  const handleSearch = () => {
    analyzeAndHighlightToxicClauses();
  };

  const uploadPdf = async (file: File) => {
    try {
      setIsLoading(true);
      setError(null);

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/pdf-upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to upload PDF');
      }

      const data = await response.json();
      console.log(data)
      return data;
    } catch (error) {
      console.error('Error uploading PDF:', error);
      setError(error instanceof Error ? error.message : 'Failed to upload PDF');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      try {
        const result = await uploadPdf(file);
        console.log('PDF uploaded successfully:', result);
        // TODO: 업로드 성공 후 처리 (예: PDF 뷰어 업데이트)
      } catch (error) {
        console.error('Failed to upload PDF:', error);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="w-full h-full rounded-lg border">
        <Skeleton className="w-full h-full" />
      </div>
    )
  }

  const addHighlight = (highlight: CustomHighlight) => {
    setHighlights([...highlights, highlight])
    if (highlight.content?.text && onTextSelect) {
      onTextSelect(highlight.content.text)
    }
  }

  const updateHighlight = (id: string, edit: Partial<CustomHighlight>) => {
    setHighlights(
      highlights.map((h) => (h.id === id ? { ...h, ...edit } : h))
    )
  }

  const handleAreaCapture = async (image: string, position: any) => {
    try {
      const result = await sendAreaToBackend({
        image,
        position,
      })

      if (result.error) {
        throw new Error(result.error)
      }

      // Update the highlight with the analysis result
      const highlightToUpdate = highlights.find(
        h => 
          h.position.pageNumber === position.pageNumber &&
          h.position.boundingRect.x1 === position.boundingRect.x1 &&
          h.position.boundingRect.y1 === position.boundingRect.y1
      )

      if (highlightToUpdate) {
        updateHighlight(highlightToUpdate.id, {
          imageUrl: image,
          comment: result.analysis,
        })
      }

      toast({
        title: "Analysis complete",
        description: result.analysis || "Area has been analyzed successfully",
      })
    } catch (error) {
      console.error('Error handling area capture:', error)
      toast({
        title: "Analysis failed",
        description: "Failed to analyze the captured area",
        variant: "destructive",
      })
    }
  }

  if (!url) {
    return (
      <div className="w-full h-full rounded-lg border flex items-center justify-center">
        <p className="text-muted-foreground">No PDF document loaded</p>
      </div>
    )
  }

  return (
    <div className="w-full h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-lg font-semibold">PDF Viewer</h2>
        <div className="flex items-center gap-4">
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
            id="pdf-upload"
          />
          <label
            htmlFor="pdf-upload"
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 cursor-pointer"
          >
            Upload PDF
          </label>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center p-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      )}

      {error && (
        <div className="p-4 text-red-500">
          {error}
        </div>
      )}

      <div className="w-full h-full rounded-lg border relative">
        <PdfLoader
          document={url}
        >
          {(pdfDocument) => (
            <PdfHighlighter
              pdfDocument={pdfDocument}
              enableAreaSelection={(event) => event.altKey}
              highlights={highlights}
              onSelectionFinished={(position, content) => {
                addHighlight({
                  id: Math.random().toString(16).slice(2),
                  content,
                  position,
                  comment: "",
                  category: "default",
                })
              }}
              selectionTip={<SelectionTip />}
              utilsRef={(_utils) => {
                if (highlighterUtilsRef.current) {
                  highlighterUtilsRef.current = _utils
                }
              }}
            >
              <HighlightContainer 
                editHighlight={updateHighlight}
                onAreaCapture={handleAreaCapture}
              />
            </PdfHighlighter>
          )}
        </PdfLoader>
      </div>
    </div>
  )
}
