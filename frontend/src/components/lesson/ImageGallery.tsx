import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { GalleryImage } from "../../lib/types";

interface ImageGalleryProps {
  images: GalleryImage[];
}

/** Grid of illustrative technical images with attribution and a simple lightbox. */
export default function ImageGallery({ images }: ImageGalleryProps) {
  const { t } = useTranslation();
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  useEffect(() => {
    if (openIndex === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenIndex(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openIndex]);

  if (images.length === 0) return null;
  const open = openIndex !== null ? images[openIndex] : null;

  return (
    <section className="card p-5" aria-label={t("visualGallery")}>
      <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted">
        🖼️ {t("visualGallery")}
      </h2>
      <div className={`grid gap-3 ${images.length > 1 ? "sm:grid-cols-2" : ""}`}>
        {images.map((img, i) => (
          <figure key={img.src} className="min-w-0">
            <motion.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              className="block w-full cursor-zoom-in overflow-hidden rounded-lg border border-border bg-white"
              onClick={() => setOpenIndex(i)}
              aria-label={`${img.title} — ${t("visualGallery")}`}
            >
              <img
                src={img.src}
                alt={img.title}
                loading="lazy"
                className="mx-auto max-h-52 w-full object-contain p-2"
              />
            </motion.button>
            <figcaption className="mt-1.5 truncate text-2xs text-muted" title={img.title}>
              {img.title} · {img.license}{" "}
              {img.source_url && (
                <a
                  href={img.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent hover:underline"
                >
                  ({t("imageSource")})
                </a>
              )}
            </figcaption>
          </figure>
        ))}
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-3 sm:p-6"
            role="dialog"
            aria-modal="true"
            aria-label={open.title}
            onClick={() => setOpenIndex(null)}
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              className="max-h-full max-w-[95vw] overflow-auto rounded-xl bg-surface p-4 sm:max-w-4xl"
              onClick={(e) => e.stopPropagation()}
            >
              <img src={open.src} alt={open.title} className="mx-auto max-h-[75vh] rounded-md bg-white object-contain p-2" />
              <div className="mt-3 flex items-center justify-between gap-4">
                <p className="text-xs text-muted">
                  {open.title} · {open.license}
                  {open.author && ` · ${open.author}`}
                </p>
                <button className="btn" onClick={() => setOpenIndex(null)}>
                  {t("close")}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
