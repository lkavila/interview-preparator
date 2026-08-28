import useEmblaCarousel from "embla-carousel-react";
import { motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { GalleryImage } from "../../lib/types";

interface FunFactCarouselProps {
  facts: string[];
  /** optional topic images interleaved with the facts */
  images?: GalleryImage[];
  source: "llm" | "fallback";
}

type Slide = { kind: "fact"; text: string } | { kind: "image"; image: GalleryImage };

/** Embla-powered carousel of fun facts (and optional illustrative images). */
export default function FunFactCarousel({ facts, images = [], source }: FunFactCarouselProps) {
  const { t } = useTranslation();
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true, align: "center" });
  const [selected, setSelected] = useState(0);

  const slides: Slide[] = [
    ...facts.map((text): Slide => ({ kind: "fact", text })),
    ...images.slice(0, 2).map((image): Slide => ({ kind: "image", image })),
  ];

  const onSelect = useCallback(() => {
    if (emblaApi) setSelected(emblaApi.selectedScrollSnap());
  }, [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    emblaApi.on("select", onSelect);
    return () => {
      emblaApi.off("select", onSelect);
    };
  }, [emblaApi, onSelect]);

  if (slides.length === 0) return null;

  return (
    <section className="card p-5" aria-label={t("funFacts")}>
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-xs font-medium uppercase tracking-wider text-muted">
          💡 {t("funFacts")}
        </h2>
        <span className="rounded bg-accent-soft px-2 py-0.5 text-2xs font-medium text-accent">
          {source === "llm" ? t("aiGenerated") : t("fallbackContent")}
        </span>
      </div>

      <div className="overflow-hidden" ref={emblaRef} aria-roledescription="carousel">
        <div className="flex">
          {slides.map((slide, i) => (
            <div
              key={i}
              className="min-w-0 flex-[0_0_100%] px-1"
              role="group"
              aria-roledescription="slide"
              aria-label={`${i + 1} / ${slides.length}`}
            >
              {slide.kind === "fact" ? (
                <div className="flex min-h-28 items-center justify-center rounded-lg border border-border bg-surface2/60 px-6 py-5">
                  <p className="max-w-lg text-center text-base leading-relaxed">{slide.text}</p>
                </div>
              ) : (
                <figure className="flex min-h-28 flex-col items-center rounded-lg border border-border bg-surface2/60 p-4">
                  <img
                    src={slide.image.src}
                    alt={slide.image.title}
                    loading="lazy"
                    className="max-h-56 rounded-md bg-white object-contain p-1"
                  />
                  <figcaption className="mt-2 text-center text-2xs text-muted">
                    {slide.image.title} — {slide.image.license}{" "}
                    {slide.image.source_url && (
                      <a
                        href={slide.image.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-accent hover:underline"
                      >
                        ({t("imageSource")})
                      </a>
                    )}
                  </figcaption>
                </figure>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <button
          className="btn px-3 py-1 text-xs"
          onClick={() => emblaApi?.scrollPrev()}
          aria-label={t("previous")}
        >
          ←
        </button>
        <div className="flex gap-1.5" role="tablist" aria-label={t("funFacts")}>
          {slides.map((_, i) => (
            <motion.button
              key={i}
              role="tab"
              aria-selected={selected === i}
              aria-label={`${i + 1}`}
              onClick={() => emblaApi?.scrollTo(i)}
              animate={{ scale: selected === i ? 1.25 : 1 }}
              className={`h-2 w-2 rounded-full ${selected === i ? "bg-accent" : "bg-border"}`}
            />
          ))}
        </div>
        <button
          className="btn px-3 py-1 text-xs"
          onClick={() => emblaApi?.scrollNext()}
          aria-label={t("next")}
        >
          →
        </button>
      </div>
    </section>
  );
}
