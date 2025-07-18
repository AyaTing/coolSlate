import { Link } from "@tanstack/react-router";
import { type ReactNode } from "react";
import photoImage_1 from "../assets/images/photo_1.jpg";
import installImage from "../assets/images/install_2.png";
import maintenanceImage from "../assets/images/maintenance.png";
import repairImage from "../assets/images/repair.png";

interface ServiceItemCardProps {
  title: string;
  description: string;
  ctaText: string;
  ctaLink?: string;
  imageElement: ReactNode;
}

const ServiceItemCard = ({
  title,
  description,
  ctaText,
  ctaLink = "/service",
  imageElement,
}: ServiceItemCardProps) => {
  return (
    <div className=" p-10 rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200/50 hover:border-[var(--color-brand-primary)]/50 flex flex-col">
      <div className="text-3xl text-[var(--color-brand-primary)]">
        {imageElement}
      </div>
      <h3 className="text-3xl font-semibold mb-5 text-[var(--color-text-primary)] mx-auto">
        {title}
      </h3>
      <p className="text-[var(--color-text-primary)] text-base mb-5 flex-grow min-h-[2.5rem] mx-auto">
        {description}
      </p>
      <Link
        to={ctaLink}
        className="self-start text-lg font-medium text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-light)] group mx-auto "
      >
        {ctaText}
        <span
          aria-hidden="true"
          className="ml-1 transition-transform duration-200 ease-in-out group-hover:translate-x-1"
        >
          →
        </span>
      </Link>
    </div>
  );
};

const HomePage = () => {
  const Images = {
    installImg: <img src={installImage} />,
    maintenanceImg: <img src={maintenanceImage} />,
    repairImg: <img src={repairImage} />,
  };

  return (
    <div className="container  mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12 space-y-16 md:space-y-24">
      <section className="grid md:grid-cols-12 gap-8 items-center bg-[var(--color-brand-primary)] p-5 rounded-3xl">
        <div className="md:col-span-6 lg:col-span-5 space-y-6 text-center md:text-left">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-[var(--color-brand-secondary)] leading-tight">
            冷氣服務，
            <br />
            <span className="text-[var(--color-text-secondary)]">
              預約不再麻煩。
            </span>
          </h1>
          <p className="text-base sm:text-lg text-[var(--color-text-secondary)]">
            維修、安裝、保養，一站式解決您的冷氣問題。
          </p>
          <Link
            to="/service"
            className="inline-block bg-[var(--color-brand-secondary)] hover:opacity-90 text-[var(--color-text-on-secondary)] font-bold py-3 px-8 rounded-lg text-lg shadow-md hover:shadow-lg transition-transform hover:scale-105 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[var(--color-brand-secondary)]"
          >
            立即開始預約
          </Link>
        </div>
        <div className=" bg-[var(--color-bg-main)] rounded-3xl md:col-span-6 lg:col-span-7">
          <img src={photoImage_1} alt="首圖照片" className="rounded-3xl" />
        </div>
      </section>
      <div className="grid sm:grid-cols-3 gap-4 lg:gap-6 p-3 md:p-4 bg-gradient-to-br from-[var(--color-brand-primary-light)]/10 via-transparent to-[var(--color-brand-secondary)] rounded-xl shadow-sm">
        <ServiceItemCard
          imageElement={Images.installImg}
          title="新機安裝"
          description="新機安裝，提供標準化安裝服務。"
          ctaText="預約安裝"
          ctaLink="/service?type=新機安裝"
        />
        <ServiceItemCard
          imageElement={Images.maintenanceImg}
          title="冷氣保養"
          description="冷氣深度清潔保養，提升效能，吹出健康風。"
          ctaText="預約清洗"
          ctaLink="/service?type=冷氣保養"
        />
        <ServiceItemCard
          imageElement={Images.repairImg}
          title="冷氣維修"
          description="不冷、漏水、異音？專業師傅快速檢測修復。"
          ctaText="預約維修"
          ctaLink="/service?type=冷氣維修"
        />
      </div>
    </div>
  );
};
export default HomePage;
