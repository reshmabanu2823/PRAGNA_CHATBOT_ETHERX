const ImageStudioPage = ({
  imagePrompt,
  setImagePrompt,
  imageStyle,
  setImageStyle,
  imageQuality,
  setImageQuality,
  imageSize,
  setImageSize,
  isGeneratingImage,
  generatedImage,
  imageError,
  onGenerate,
  onSendToChat,
}) => {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '40px', animation: 'fadeUp 0.4s ease', height: '100%' }}>
      <h1 style={{ margin: '0 0 6px 0', fontSize: '28px', fontWeight: 700, color: 'var(--pragna-text)' }}>Image Studio</h1>
      <p style={{ margin: '0 0 26px 0', fontSize: '14.5px', color: 'var(--pragna-text-muted)' }}>Generate production-quality AI images with style and quality controls.</p>

      <div style={{ maxWidth: '760px', padding: '24px', borderRadius: '20px', background: 'var(--pragna-surface)', border: '1px solid rgba(212,175,55,0.18)', backdropFilter: 'blur(8px)', boxShadow: '0 12px 28px rgba(0,0,0,0.42)' }}>
        
        {/* Prompt textarea */}
        <textarea
          value={imagePrompt}
          onChange={(e) => setImagePrompt(e.target.value)}
          placeholder="Describe the image in detail. Example: A hyper-real product photo of a matte black smartwatch on floating glass with soft studio light."
          rows="4"
          style={{
            width: '100%',
            resize: 'vertical',
            borderRadius: '12px',
            border: '1px solid var(--pragna-border)',
            background: 'var(--pragna-surface)',
            color: 'var(--pragna-text)',
            fontFamily: 'inherit',
            fontSize: '14.5px',
            lineHeight: 1.55,
            padding: '14px 16px',
            marginBottom: '16px',
          }}
        />

        {/* Dropdowns */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
          <select
            value={imageStyle}
            onChange={(e) => setImageStyle(e.target.value)}
            style={{ flex: 1, minWidth: '150px', padding: '11px 14px', borderRadius: '11px', border: '1px solid var(--pragna-border)', background: 'var(--pragna-surface)', color: 'var(--pragna-text)', fontFamily: 'inherit', fontSize: '13.5px', cursor: 'pointer' }}
          >
            <option value="cinematic">Cinematic</option>
            <option value="photo">Photo</option>
            <option value="illustration">Illustration</option>
            <option value="concept_art">Concept Art</option>
            <option value="product">Product</option>
          </select>

          <select
            value={imageQuality}
            onChange={(e) => setImageQuality(e.target.value)}
            style={{ flex: 1, minWidth: '150px', padding: '11px 14px', borderRadius: '11px', border: '1px solid var(--pragna-border)', background: 'var(--pragna-surface)', color: 'var(--pragna-text)', fontFamily: 'inherit', fontSize: '13.5px', cursor: 'pointer' }}
          >
            <option value="hd">HD</option>
            <option value="standard">Standard</option>
            <option value="draft">Draft</option>
          </select>

          <select
            value={imageSize}
            onChange={(e) => setImageSize(e.target.value)}
            style={{ flex: 1, minWidth: '150px', padding: '11px 14px', borderRadius: '11px', border: '1px solid var(--pragna-border)', background: 'var(--pragna-surface)', color: 'var(--pragna-text)', fontFamily: 'inherit', fontSize: '13.5px', cursor: 'pointer' }}
          >
            <option value="1024x1024">Square (1024x1024)</option>
            <option value="1024x1536">Portrait (1024x1536)</option>
            <option value="1536x1024">Landscape (1536x1024)</option>
          </select>
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: imageError || generatedImage?.image ? '20px' : 0 }}>
          <button
            onClick={onGenerate}
            disabled={isGeneratingImage || !imagePrompt.trim()}
            style={{
              flex: 1,
              padding: '12px 20px',
              borderRadius: '12px',
              border: 'none',
              background: 'linear-gradient(135deg, var(--pragna-gold-soft), var(--pragna-gold-deep))',
              color: 'var(--pragna-bg)',
              fontSize: '14.5px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 6px 18px rgba(0,0,0,0.34), 0 0 16px rgba(212,175,55,0.22)',
              transition: 'all 0.15s ease',
              opacity: (isGeneratingImage || !imagePrompt.trim()) ? 0.5 : 1,
            }}
            className="hover:shadow-[0_6px_18px_rgba(0,_0,_0,_0.34),_0_0_26px_rgba(212,_175,_55,_0.4)]"
          >
            {isGeneratingImage ? 'Generating...' : 'Generate Image'}
          </button>
          <button
            onClick={onSendToChat}
            style={{
              padding: '12px 20px',
              borderRadius: '12px',
              border: '1px solid var(--pragna-border)',
              background: 'transparent',
              color: 'var(--pragna-text-muted)',
              fontSize: '14.5px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            className="hover:text-[var(--pragna-gold-soft)] hover:border-accent-500/40"
          >
            Send Prompt to Chat
          </button>
        </div>

        {imageError && (
          <div style={{ marginTop: '16px', padding: '12px 16px', borderRadius: '10px', background: 'rgba(180,60,60,0.15)', border: '1px solid rgba(220,110,100,0.35)', color: '#e8a598', fontSize: '13.5px' }}>
            {imageError}
          </div>
        )}

        {generatedImage?.image && (
          <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <img
              src={generatedImage.image}
              alt="Generated AI"
              style={{ width: '100%', borderRadius: '12px', border: '1px solid var(--pragna-border)', objectFit: 'cover' }}
            />
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
              <a
                href={generatedImage.image}
                download="pragna-generated-image.png"
                style={{ padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--pragna-border)', textDecoration: 'none', color: 'var(--pragna-gold-soft)', fontSize: '13px', fontWeight: 600 }}
                className="hover:bg-[var(--pragna-surface-2)]"
              >
                Download Image
              </a>
              <span style={{ fontSize: '12px', color: 'var(--pragna-text-muted)' }}>
                Model: {generatedImage.model || 'DALL-E'} | Style: {imageStyle}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ImageStudioPage
